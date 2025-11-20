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
        ui.markdown('# 📊 Slides Editor')
        ui.markdown('*Upload reveal.js ZIP → Auto-detect slides → Upload to Slides.com*')
        
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
                    '🟢 Running' if is_running else '🔴 Stopped',
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
                ui.label(f'📦 Current: {folder_name}').classes('text-grey-7 mb-2')
            
            # Simple upload button (styled to match CREATE DECK)
            ui.upload(
                label='📁 Select ZIP File',
                on_upload=self._handle_zip_upload,
                auto_upload=True,
                multiple=False
            ).props('accept=".zip" color="primary"').classes('w-full')
    
    def _render_file_info(self):
        """Show detected files from uploaded ZIP."""
        with ui.card().classes('w-full'):
            ui.label('Detected Files').classes('text-h6')
            
            if not self.session.extracted_folder:
                ui.label('ℹ️ Upload a ZIP file above to see detected files').classes('text-grey-7')
                return
            
            # Reveal.js slides
            if self.session.reveal_slides:
                ui.label(f'✅ Found {len(self.session.reveal_slides)} reveal.js slide(s)').classes('text-green-7 font-bold')
                for slide_file in self.session.reveal_slides:
                    rel_path = slide_file.relative_to(self.session.extracted_folder)
                    ui.label(f'  📄 {rel_path}').classes('ml-4 text-sm')
            else:
                ui.label('⚠️ No reveal.js slides detected').classes('text-orange-7')
            
            ui.space()
            
            # Plot files
            if self.session.plot_files:
                ui.label(f'📊 {len(self.session.plot_files)} plot HTML file(s)').classes('text-blue-7')
                ui.label('These will be served via HTTPS for embedding').classes('text-sm text-grey-7')
            else:
                ui.label('ℹ️ No additional HTML files found').classes('text-grey-7')
            
            # Future: User uploads section placeholder
            ui.space()
            ui.label('💡 Future: Add custom files from other projects here').classes('text-sm text-grey-5 italic')
    
    def _render_upload_section(self):
        """Render upload to Slides.com button."""
        with ui.card().classes('w-full'):
            ui.label('Upload to Slides.com').classes('text-h6')
            
            has_slides = len(self.session.reveal_slides) > 0
            server_running = self.session.server_running
            
            btn = ui.button(
                '⬆️ Create Deck (Opens Browser)',
                on_click=self._upload_to_slides,
                icon='cloud_upload',
                color='primary'
            ).classes('w-full')
            
            # Enable only if prerequisites met
            btn.enabled = has_slides and server_running
            
            # Show status
            if not server_running:
                ui.label('⚠️ Start server before uploading').classes('text-orange-7')
            elif not has_slides:
                ui.label('⚠️ Upload a ZIP with reveal.js slides first').classes('text-orange-7')
            else:
                ui.label('✅ Ready to upload').classes('text-green-7')
    
    def _render_download_section(self):
        """Render download & reconstitute section."""
        with ui.card().classes('w-full'):
            ui.label('Download & Reconstitute').classes('text-h6')
            ui.label('Download from Slides.com and convert back to local paths').classes('text-sm text-grey-7')
            
            ui.upload(
                label='📥 Select Downloaded ZIP',
                on_upload=self._handle_download_reconstitute,
                auto_upload=True,
                multiple=False
            ).props('accept=".zip" color="secondary"').classes('w-full')
            
            ui.label('ℹ️ Converts HTTPS URLs back to local paths for client delivery').classes('text-sm text-grey-5 mt-2')
    
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
            
            # Update session state
            self.session.extracted_folder = extract_folder
            
            # Detect files
            self._update_status('Detecting files...')
            self.session.reveal_slides, self.session.plot_files = find_html_files(extract_folder)
            
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
            self._update_status(f'✅ Deck opened. Plots at {base_url}')
            
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
                # Convert local path to HTTPS URL
                if not old_path.startswith('http'):
                    try:
                        # URL-encode for special characters (#, spaces, etc.)
                        encoded_path = quote(old_path, safe='/')
                        block['value'] = f"{base_url}/plots/{encoded_path}"
                    except Exception as e:
                        logger.warning(f"Could not transform URL {old_path}: {e}")
    
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
            # Pattern: https://localhost:8766/plots/... → data/...
            https_port = self.config.local_server_port + 1
            base_https = f'https://localhost:{https_port}/plots/'
            
            # Simple replacement: HTTPS server URLs → data/ folder
            html_content = html_content.replace(base_https, 'data/')
            
            # Also decode URL-encoded characters
            from urllib.parse import unquote
            # Find all data/ references and decode them
            import re
            def decode_path(match):
                path = match.group(1)
                return f'"data/{unquote(path)}"'
            
            html_content = re.sub(r'"data/([^"]+)"', decode_path, html_content)
            
            # Write updated index.html
            index_file.write_text(html_content, encoding='utf-8')
            
            # Copy plot files to data/ folder if we have session data
            if self.session.extracted_folder and self.session.extracted_folder.exists():
                data_folder = download_folder / 'data'
                data_folder.mkdir(exist_ok=True)
                
                self._update_status('Copying plot files...')
                # Copy all plot files from session
                for plot_file in self.session.plot_files:
                    rel_path = plot_file.relative_to(self.session.extracted_folder)
                    dest_file = data_folder / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(plot_file, dest_file)
            
            # Success - open folder
            ui.notify(f'✅ Reconstituted deck ready at: {download_folder}', type='positive', timeout=5000)
            self._update_status(f'Ready at: {download_folder}')
            
            # Open in file explorer
            import subprocess
            subprocess.run(['explorer', str(download_folder)])
            
        except Exception as e:
            logger.error(f'Error reconstituting download: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error processing download')
    
    def _update_status(self, message: str):
        """Update status label."""
        if self.status_label:
            self.status_label.text = message
