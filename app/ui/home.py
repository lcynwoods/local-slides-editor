# -*- coding: utf-8 -*-
"""
Simplified home page - ZIP upload workflow with manual server control.
"""
from nicegui import ui
from pathlib import Path
from typing import Optional
import logging
import tempfile
import shutil
from urllib.parse import quote
import base64
import mimetypes
import hashlib
import re
import uuid
import json

from ..config import Config
from ..slides_api import create_deck_via_define_api
from ..utils.zip_utils import extract_deck_zip
from ..utils.reveal_detector import find_html_files
from ..utils.html_to_json import parse_html_deck

logger = logging.getLogger(__name__)


class HomePage:
    """Simplified home page with ZIP-based workflow."""
    
    def __init__(self, config: Config, session, app_instance):
        self.config = config
        self.session = session  # In-memory session state
        self.app_instance = app_instance  # For server control
        self.status_label: Optional[ui.label] = None
        self.main_container: Optional[ui.column] = None

        ui.colors(primary="#DB5400")
    
    def _detect_data_folder(self) -> tuple[str, Optional[Path]]:
        """Detect the data folder name and path within the extracted session."""
        default_name = 'data'
        if not self.session.extracted_folder or not self.session.extracted_folder.exists():
            return default_name, None

        base = self.session.extracted_folder

        for item in base.iterdir():
            if item.is_dir() and item.name.endswith('_data'):
                return item.name, item

        for item in base.iterdir():
            if item.is_dir():
                return item.name, item

        fallback_path = base / default_name
        fallback_path.mkdir(parents=True, exist_ok=True)
        return default_name, fallback_path

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard via browser JavaScript."""
        escaped = json.dumps(text)
        ui.run_javascript(f'navigator.clipboard.writeText({escaped});')
        ui.notify('Copied to clipboard', type='positive', timeout=1500)

    def render(self):
        """Render the home page."""
        # Clear and re-render if container exists
        if self.main_container is not None:
            self.main_container.clear()
            with self.main_container:
                self._render_content()
        else:
            self.main_container = ui.column().classes('w-full max-w-4xl mx-auto p-4')
            with self.main_container:
                self._render_content()
    
    def _render_content(self):
        """Render page content."""
        ui.markdown('# Slides Editor')
        ui.markdown('*Upload reveal.js ZIP, auto-detect slides, upload to Slides.com*')
        
        ui.separator()
        
        # Server controls
        self._render_server_section()
        
        ui.separator()
        
        # ZIP upload
        self._render_zip_section()
        
        ui.separator()
        
        # File info (what was detected)
        self._render_file_info()
        
        ui.separator()
        
        # Custom assets
        self._render_custom_assets_section()

        ui.separator()

        # Upload to Slides.com
        self._render_upload_section()
        
        ui.separator()
        
        # Download & Reconstitute
        self._render_download_section()
        
        ui.separator()
        
        # Status
        with ui.card().classes('w-full'):
            ui.label('Status').classes('text-h6')
            self.status_label = ui.label('Ready').classes('text-grey-7')
    
    def _render_server_section(self):
        """Render server start/stop controls."""
        with ui.card().classes('w-full'):
            ui.label('Plot Server').classes('text-h6')
            
            with ui.row().classes('w-full items-center gap-2'):
                is_running = self.session.server_running
                status_badge = ui.badge(
                    'Running' if is_running else 'Stopped',
                    color='positive' if is_running else 'negative'
                )
                
                if is_running:
                    port = self.config.local_server_port
                    ui.label(f'HTTP: localhost:{port} | HTTPS: localhost:{port+1}').classes('text-sm text-grey-7')
                
                ui.space()
                
                if not is_running:
                    ui.button(
                        'Start Server',
                        on_click=self._start_server,
                        icon='play_arrow',
                        color='positive'
                    )
                else:
                    ui.button(
                        'Stop Server',
                        on_click=self._stop_server,
                        icon='stop',
                        color='negative'
                    )
    
    def _render_zip_section(self):
        """Render ZIP file upload."""
        with ui.card().classes('w-full'):
            ui.label('Upload Deck ZIP').classes('text-h6')
            ui.label('Select a ZIP containing your reveal.js presentation').classes('text-sm text-grey-7')
            
            if self.session.extracted_folder:
                folder_name = self.session.extracted_folder.name
                ui.label(f'Current: {folder_name}').classes('text-grey-7 mb-2')
            
            # Simple upload button
            ui.upload(
                label='Select ZIP File',
                on_upload=self._handle_zip_upload,
                auto_upload=True,
                multiple=False
            ).props('accept=".zip"').classes('w-full')
    
    def _render_file_info(self):
        """Show detected files from uploaded ZIP."""
        with ui.card().classes('w-full'):
            ui.label('Detected Files').classes('text-h6')
            
            if not self.session.extracted_folder:
                ui.label('Upload a ZIP file above to see detected files').classes('text-grey-7')
                return
            
            # Reveal.js slides
            if self.session.reveal_slides:
                ui.label(f'Found {len(self.session.reveal_slides)} reveal.js slide(s)').classes('text-green-7 font-bold')
                for slide_file in self.session.reveal_slides:
                    rel_path = slide_file.relative_to(self.session.extracted_folder)
                    ui.label(f'  {rel_path}').classes('ml-4 text-sm')
            else:
                ui.label('No reveal.js slides detected').classes('text-orange-7')
            
            ui.space()
            
            # Plot files
            if self.session.plot_files:
                ui.label(f'{len(self.session.plot_files)} plot HTML file(s)').classes('text-orange-7')
                ui.label('These will be served via HTTPS for embedding').classes('text-sm text-grey-7')
            else:
                ui.label('No additional HTML files found').classes('text-grey-7')
    
    def _render_custom_assets_section(self):
        """Render section for user-added custom assets."""
        with ui.card().classes('w-full'):
            ui.label('Custom Assets').classes('text-h6')
            ui.label('Add additional HTML plots or images from other projects.').classes('text-sm text-grey-7')
            ui.label('Files are hosted like other plots and bundled during reconstitution.').classes('text-sm text-grey-7 mb-2')
            ui.label('Use the copied relative path as the block URL when editing in Slides.com.').classes('text-sm text-grey-7 mb-2')

            if not self.session.extracted_folder:
                ui.label('Upload a deck ZIP before adding custom assets.').classes('text-grey-7')
                return

            ui.upload(
                label='Add HTML or Image',
                on_upload=self._handle_custom_asset_upload,
                auto_upload=True,
                multiple=True
            ).props('accept=".html,.htm,.png,.jpg,.jpeg,.gif,.svg"').classes('w-full')

            if not self.session.custom_assets:
                ui.space()
                ui.label('No custom assets added yet.').classes('text-grey-7')
                return

            ui.space()
            ui.label(f'{len(self.session.custom_assets)} custom asset(s) added').classes('text-orange-7 font-bold')

            https_port = self.config.local_server_port + 1

            for asset in self.session.custom_assets:
                rel_path = asset['relative_path']
                is_html = asset['is_html']
                icon = 'article' if is_html else 'image'
                encoded_path = quote(rel_path, safe='/')
                served_url = f'https://localhost:{https_port}/plots/{encoded_path}'
                with ui.row().classes('items-center w-full gap-2 no-wrap'):
                    ui.icon(icon)
                    ui.label(rel_path).classes('text-sm font-mono truncate flex-1')
                    ui.button(
                        'Copy URL',
                        on_click=lambda url=served_url: self._copy_to_clipboard(url),
                        icon='content_copy',
                    ).props('flat size=small color=orange')
                    if self.session.server_running:
                        ui.button(
                            'Open',
                            on_click=lambda url=served_url: ui.navigate.to(url, new_tab=True),
                            icon='open_in_new'
                        ).props('flat size=small color=orange')
    def _render_upload_section(self):
        """Render upload to Slides.com button."""
        with ui.card().classes('w-full'):
            ui.label('Upload to Slides.com').classes('text-h6')
            
            has_slides = len(self.session.reveal_slides) > 0
            server_running = self.session.server_running
            
            btn = ui.button(
                'Create Deck (Opens Browser)',
                on_click=self._upload_to_slides,
                icon='cloud_upload'
            ).classes('w-full')
            
            # Enable only if prerequisites met
            btn.enabled = has_slides and server_running
            
            # Show status
            if not server_running:
                ui.label('Start server before uploading').classes('text-orange-7')
            elif not has_slides:
                ui.label('Upload a ZIP with reveal.js slides first').classes('text-orange-7')
            else:
                ui.label('Ready to upload').classes('text-green-7')
    
    def _render_download_section(self):
        """Render download & reconstitute section."""
        with ui.card().classes('w-full'):
            ui.label('Download & Reconstitute').classes('text-h6')
            ui.label('Download from Slides.com and convert back to local paths for client delivery.').classes('text-sm text-grey-7')
            
            # Step 1: Output folder selection
            ui.label('Step 1: Select output location').classes('text-sm font-bold mt-2')
            with ui.row().classes('w-full items-center gap-2'):
                ui.label('Output folder:').classes('text-sm')
                self.output_folder_label = ui.label(
                    str(self.config.output_folder) if self.config.output_folder else 'Not set'
                ).classes('text-sm text-grey-7 flex-1 truncate')
                ui.button(
                    'Browse',
                    on_click=self._select_output_folder,
                    icon='folder'
                ).props('flat size=small color=orange')
            
            # Show where files will be saved (with auto-generated subfolder)
            if self.config.output_folder:
                ui.label('A new subfolder will be created for each reconstituted deck.').classes('text-xs text-grey-6')
            
            ui.separator().classes('my-2')
            
            # Step 2: Upload ZIP (only enabled if folder is set)
            ui.label('Step 2: Upload ZIP from Slides.com').classes('text-sm font-bold')
            
            has_output_folder = self.config.output_folder is not None
            
            if has_output_folder:
                self.download_upload = ui.upload(
                    label='Select Downloaded ZIP',
                    on_upload=self._handle_download_reconstitute,
                    auto_upload=True,
                    multiple=False
                ).props('accept=".zip"').classes('w-full')
            else:
                ui.label('Select an output folder first to enable ZIP upload.').classes('text-orange-7 text-sm')
                # Disabled placeholder
                with ui.row().classes('w-full items-center justify-center p-4 bg-grey-2 rounded'):
                    ui.icon('cloud_upload', size='lg').classes('text-grey-5')
                    ui.label('ZIP upload disabled').classes('text-grey-5')
    
    async def _select_output_folder(self):
        """Open folder picker for output location."""
        # Use JavaScript to trigger folder selection
        result = await ui.run_javascript('''
            return new Promise((resolve) => {
                const input = document.createElement('input');
                input.type = 'file';
                input.webkitdirectory = true;
                input.onchange = () => {
                    if (input.files.length > 0) {
                        resolve(input.files[0].webkitRelativePath.split('/')[0]);
                    } else {
                        resolve(null);
                    }
                };
                input.click();
            });
        ''', timeout=60)
        # Note: Browser folder picker is limited; for now show dialog to enter path
        await self._show_output_folder_dialog()
    
    async def _show_output_folder_dialog(self):
        """Show dialog to enter output folder path."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Set Output Folder').classes('text-h6')
            ui.label('Enter the full path where reconstituted decks should be saved:').classes('text-sm text-grey-7')
            ui.label('A new subfolder will be created for each deck to avoid conflicts.').classes('text-xs text-grey-6 mb-2')
            
            folder_input = ui.input(
                'Output folder path',
                value=str(self.config.output_folder) if self.config.output_folder else ''
            ).classes('w-full')
            folder_input.props('outlined')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                
                async def save_folder():
                    path = folder_input.value.strip()
                    if path:
                        folder_path = Path(path)
                        # Create the folder if it doesn't exist
                        folder_path.mkdir(parents=True, exist_ok=True)
                        self.config.output_folder = folder_path
                        ui.notify(f'Output folder set to: {path}', type='positive')
                    else:
                        self.config.output_folder = None
                        ui.notify('Output folder cleared', type='info')
                    dialog.close()
                    # Refresh page to update the upload section
                    ui.navigate.to('/')
                
                ui.button('Save', on_click=save_folder).props('color=orange')
        
        dialog.open()
    
    async def _handle_zip_upload(self, e):
        """Handle ZIP file upload and extraction."""
        try:
            self._update_status('Uploading...')
            
            # Get file content
            filename = e.file.name
            content = await e.file.read()
            
            # Save to temp
            temp_zip = Path(tempfile.gettempdir()) / filename
            temp_zip.write_bytes(content)
            
            self._update_status(f'Extracting {filename}...')
            
            # Extract to temp folder
            extract_base = Path(tempfile.gettempdir()) / 'slides_editor_session'
            extract_base.mkdir(parents=True, exist_ok=True)
            
            # Clear old session
            if self.session.extracted_folder and self.session.extracted_folder.exists():
                shutil.rmtree(self.session.extracted_folder)
            
            # Extract new ZIP
            extract_folder = extract_base / temp_zip.stem
            extract_folder.mkdir(parents=True, exist_ok=True)
            extract_deck_zip(temp_zip, extract_folder)
            
            # Reset session state while preserving server status
            server_running = self.session.server_running
            self.session.reset()
            self.session.server_running = server_running

            # Update session state
            self.session.extracted_folder = extract_folder
            
            # Detect files
            self._update_status('Detecting files...')
            self.session.reveal_slides, self.session.plot_files = find_html_files(extract_folder)
            self.session.custom_assets = []
            
            # Update server folder
            self.app_instance.update_server_folder(extract_folder)
            
            # Show notifications
            ui.notify(f'Extracted {filename}', type='positive')
            if self.session.reveal_slides:
                ui.notify(f'Found {len(self.session.reveal_slides)} reveal.js deck(s)!', type='positive')
            else:
                ui.notify('No reveal.js slides detected', type='warning')
            
            self._update_status('Ready')
            self.render()  # Refresh UI
            
        except Exception as e:
            logger.error(f'Error handling ZIP upload: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error uploading ZIP')
    
    async def _handle_custom_asset_upload(self, e):
        """Handle upload of custom HTML or image assets."""
        if not self.session.extracted_folder or not self.session.extracted_folder.exists():
            ui.notify('Upload a deck ZIP before adding custom assets', type='negative')
            return

        try:
            filename = Path(e.file.name).name
            if not filename:
                ui.notify('Invalid filename', type='negative')
                return

            content = await e.file.read()
            asset_id = uuid.uuid4().hex[:8]

            data_folder_name, data_folder_path = self._detect_data_folder()
            if data_folder_path is None and self.session.extracted_folder:
                data_folder_path = self.session.extracted_folder / data_folder_name
                data_folder_path.mkdir(parents=True, exist_ok=True)

            if data_folder_path is None:
                ui.notify('Could not determine data folder for custom assets', type='negative')
                return

            custom_root = data_folder_path / 'custom_assets'
            custom_root.mkdir(parents=True, exist_ok=True)

            dest_dir = custom_root / f'asset_{asset_id}'
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / filename
            dest_file.write_bytes(content)

            rel_path = dest_file.relative_to(self.session.extracted_folder).as_posix()
            asset_info = {
                'id': asset_id,
                'name': filename,
                'relative_path': rel_path,
                'is_html': dest_file.suffix.lower() in {'.html', '.htm'},
                'size': len(content)
            }

            self.session.custom_assets.append(asset_info)

            # Refresh HTML detection to include newly added files
            self.session.reveal_slides, self.session.plot_files = find_html_files(self.session.extracted_folder)

            ui.notify(f'Added custom asset: {filename}', type='positive')
            self._update_status(f'Added custom asset ({filename})')
            self.render()

        except Exception as exc:
            logger.error(f'Error adding custom asset: {exc}', exc_info=True)
            ui.notify(f'Error: {exc}', type='negative')
            self._update_status('Error adding custom asset')

    async def _start_server(self):
        """Start the plot servers."""
        try:
            self._update_status('Starting servers...')
            await self.app_instance.start_plot_server()
            ui.notify('Servers started', type='positive')
            self._update_status('Servers running')
            self.render()
        except Exception as e:
            logger.error(f'Error starting servers: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error starting servers')
    
    async def _stop_server(self):
        """Stop the plot servers."""
        try:
            self._update_status('Stopping servers...')
            await self.app_instance.stop_plot_server()
            ui.notify('Servers stopped', type='warning')
            self._update_status('Servers stopped')
            self.render()
        except Exception as e:
            logger.error(f'Error stopping servers: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error stopping servers')
    
    async def _upload_to_slides(self):
        """Upload deck to Slides.com via Define API."""
        if not self.session.reveal_slides:
            ui.notify('No reveal.js slides to upload', type='negative')
            return
        
        if not self.session.server_running:
            ui.notify('Start server before uploading', type='negative')
            return
        
        try:
            # Use first reveal.js file
            html_file = self.session.reveal_slides[0]
            
            self._update_status(f'Converting {html_file.name} to JSON...')
            
            # Parse HTML to JSON
            deck_json = parse_html_deck(html_file)
            
            # Transform URLs to HTTPS
            https_port = self.config.local_server_port + 1
            base_url = f"https://localhost:{https_port}"
            deck_json = self._transform_plot_urls(deck_json, base_url)
            
            self._update_status('Opening browser...')
            
            # Upload via Define API (opens browser)
            create_deck_via_define_api(deck_json)
            
            ui.notify(f'Deck opened in browser! Plots at {base_url}', type='positive')
            self._update_status(f'Deck opened. Plots at {base_url}')
            
        except Exception as e:
            logger.error(f'Error uploading: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error uploading')
    
    def _transform_plot_urls(self, deck_json: dict, base_url: str) -> dict:
        """Transform local plot URLs to HTTPS server URLs."""
        for slide in deck_json.get('slides', []):
            if isinstance(slide, list):
                # Vertical slides
                for sub_slide in slide:
                    self._transform_slide_urls(sub_slide, base_url)
            else:
                self._transform_slide_urls(slide, base_url)
        return deck_json
    
    def _transform_slide_urls(self, slide: dict, base_url: str):
        """Transform URLs in a single slide."""
        if not self.session.extracted_folder:
            return
        
        for block in slide.get('blocks', []):
            if block.get('type') in ['iframe', 'image'] and 'value' in block:
                old_path = block['value']
                # Convert local path to HTTPS URL or base64
                if not old_path.startswith('http'):
                    try:
                        if block.get('type') == 'image':
                            # Convert images to base64 data URLs
                            block['value'] = self._convert_image_to_base64(old_path)
                        else:
                            # For iframes, use HTTPS URL
                            # URL-encode for special characters (#, spaces, etc.)
                            encoded_path = quote(old_path, safe='/')
                            block['value'] = f"{base_url}/plots/{encoded_path}"
                    except Exception as e:
                        logger.warning(f"Could not transform URL {old_path}: {e}")
    
    def _convert_image_to_base64(self, image_path: str) -> str:
        """Convert an image file to a base64 data URL."""
        # Resolve full path
        full_path = self.session.extracted_folder / image_path
        
        if not full_path.exists():
            logger.warning(f"Image file not found: {full_path}")
            return image_path  # Return original path as fallback
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = 'image/png'  # Default fallback
        
        # Read and encode image
        with open(full_path, 'rb') as f:
            image_data = f.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # Create data URL
        data_url = f"data:{mime_type};base64,{base64_data}"
        logger.info(f"Converted image to base64: {image_path} ({len(base64_data)} chars)")
        return data_url

    def _convert_base64_to_image_paths(self, html_content: str, output_folder: Path, data_folder_name: str) -> str:
        """Convert base64 image data URLs in HTML back to file paths."""
        if not html_content:
            return html_content
        
        if not self.session.extracted_folder or not self.session.extracted_folder.exists():
            return html_content

        # Build hash map of original images for lookup
        image_map = self._build_image_hash_map()
        created_images: list[Path] = []
        created_count = 0

        pattern = re.compile(r'"data:(?P<mime>image/[^"]+?);base64,(?P<data>[^"]+)"')

        def replace(match):
            nonlocal created_count
            mime_type = match.group('mime')
            base64_data = match.group('data')

            try:
                image_bytes = base64.b64decode(base64_data)
            except Exception:
                logger.warning('Failed to decode base64 image data during reconstitution')
                return match.group(0)

            digest = hashlib.md5(image_bytes).hexdigest()

            rel_path = image_map.get(digest)
            if not rel_path:
                # Create new image file under <data_folder>/config/embedded_images
                ext = mimetypes.guess_extension(mime_type) or '.png'
                rel_path = Path(data_folder_name) / 'config' / 'embedded_images' / f'embedded_{created_count}{ext}'
                created_count += 1
                dest_file = output_folder / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_bytes(image_bytes)
                image_map[digest] = rel_path
                created_images.append(rel_path)
            return f'"{rel_path.as_posix()}"'

        updated_html = pattern.sub(replace, html_content)

        if created_images:
            logger.info(f'Created {len(created_images)} embedded image files during reconstitution')

        return updated_html

    def _build_image_hash_map(self) -> dict[str, Path]:
        """Build mapping of image file hashes to relative paths from the session."""
        image_map: dict[str, Path] = {}
        if not self.session.extracted_folder or not self.session.extracted_folder.exists():
            return image_map

        for item in self.session.extracted_folder.rglob('*'):
            if not item.is_file():
                continue
            mime_type, _ = mimetypes.guess_type(str(item))
            if not mime_type or not mime_type.startswith('image/'):
                continue
            try:
                data = item.read_bytes()
            except Exception as exc:
                logger.warning(f'Failed to read image {item}: {exc}')
                continue
            digest = hashlib.md5(data).hexdigest()
            rel_path = item.relative_to(self.session.extracted_folder)
            image_map[digest] = rel_path
        return image_map
    
    async def _handle_download_reconstitute(self, e):
        """Handle downloaded ZIP from Slides.com and reconstitute for delivery."""
        try:
            self._update_status('Processing download...')
            
            # Get file content
            filename = e.file.name
            content = await e.file.read()
            
            # Save to temp
            downloaded_zip = Path(tempfile.gettempdir()) / filename
            downloaded_zip.write_bytes(content)
            
            # Extract downloaded ZIP
            download_folder = Path(tempfile.gettempdir()) / 'slides_download' / downloaded_zip.stem
            download_folder.mkdir(parents=True, exist_ok=True)
            
            self._update_status('Extracting...')
            extract_deck_zip(downloaded_zip, download_folder)
            
            # Find index.html
            index_file = download_folder / 'index.html'
            if not index_file.exists():
                ui.notify('No index.html found in downloaded ZIP', type='negative')
                return
            
            # Read and transform URLs
            self._update_status('Converting URLs to local paths...')
            html_content = index_file.read_text(encoding='utf-8')
            
            # Replace HTTPS URLs with local paths
            # Pattern: https://localhost:8766/plots/InakiPhos_data/... → InakiPhos_data/...
            https_port = self.config.local_server_port + 1
            base_https = f'https://localhost:{https_port}/plots/'
            
            # Simple replacement: HTTPS server URLs → direct relative paths
            html_content = html_content.replace(base_https, '')
            
            # Detect the data folder name (e.g., InakiPhos_data)
            data_folder_name, _ = self._detect_data_folder()
            
            # Move lib/ references to <data_folder>/config/lib/
            html_content = html_content.replace('lib/', f'{data_folder_name}/config/lib/')
            
            # Find and move deck folder references to <data_folder>/config/
            # Pattern: Look for references to deck folders
            for item in download_folder.iterdir():
                if item.is_dir() and item.name not in ['lib']:
                    # This is likely the deck folder
                    deck_name = item.name
                    html_content = html_content.replace(f'"{deck_name}/', f'"{data_folder_name}/config/{deck_name}/')
            
            # Also decode URL-encoded characters
            from urllib.parse import unquote
            # Find all path references and decode them
            def decode_path(match):
                path = match.group(1)
                return f'"{unquote(path)}"'
            
            html_content = re.sub(r'"([^"]+)"', decode_path, html_content)
            
            # Create clean output folder - always create a new subfolder to avoid file picker warnings
            if self.config.output_folder:
                output_base = self.config.output_folder
            else:
                # Fallback to temp (shouldn't happen since upload is disabled without folder)
                output_base = Path(tempfile.gettempdir()) / 'slides_output'
            
            # Use ZIP name as subfolder (creates fresh folder each time)
            output_folder = output_base / downloaded_zip.stem
            if output_folder.exists():
                shutil.rmtree(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy all original files to root of output folder
            if self.session.extracted_folder and self.session.extracted_folder.exists():
                self._update_status('Copying all files from session...')
                
                # Copy entire extracted folder contents to output root
                # This includes: HTML plots, Excel files, TSV, CSV, images, etc.
                file_count = 0
                for item in self.session.extracted_folder.rglob('*'):
                    if item.is_file():
                        # Skip the reveal.js slide deck itself
                        if item.name in ['index.html', 'index.htm']:
                            continue
                        
                        rel_path = item.relative_to(self.session.extracted_folder)
                        dest_file = output_folder / rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(item, dest_file)
                        file_count += 1
                
                ui.notify(f'Copied {file_count} data files', type='info')
            
            # Copy lib/ and deck folders from downloaded ZIP to <data_folder>/config/
            self._update_status('Copying reveal.js infrastructure...')
            config_folder = output_folder / data_folder_name / 'config'
            config_folder.mkdir(parents=True, exist_ok=True)
            
            config_count = 0
            for item in download_folder.iterdir():
                # Skip index.html, but copy lib/ and any deck folders
                if item.name.lower() in ['index.html', 'index.htm']:
                    continue
                
                dest = config_folder / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                    # Count files in copied directory
                    config_count += sum(1 for _ in dest.rglob('*') if _.is_file())
                else:
                    shutil.copy(item, dest)
                    config_count += 1
            
            ui.notify(f'Copied {config_count} reveal.js config files to {data_folder_name}/config/', type='info')

            # Convert base64 image data URLs back to file paths
            self._update_status('Converting base64 images to file references...')
            html_content = self._convert_base64_to_image_paths(html_content, output_folder, data_folder_name)

            # Write updated index.html to output folder
            output_index = output_folder / 'index.html'
            output_index.write_text(html_content, encoding='utf-8')
            
            # Success - open folder
            ui.notify(f'Reconstituted deck ready at: {output_folder}', type='positive', timeout=5000)
            self._update_status(f'Ready at: {output_folder}')
            
            # Open in file explorer
            import subprocess
            subprocess.run(['explorer', str(output_folder)])
            
        except Exception as e:
            logger.error(f'Error reconstituting download: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error processing download')
    
    def _update_status(self, message: str):
        """Update status label."""
        if self.status_label:
            self.status_label.text = message
