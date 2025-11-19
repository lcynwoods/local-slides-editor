"""
Home page UI for slides_editor.
Main dashboard for deck management operations.
"""
from nicegui import ui, app
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import asyncio
import tempfile
from datetime import datetime

from ..config import Config
from ..slides_api import SlidesAPI, SlidesAPIError, create_deck_via_define_api
from ..utils.zip_utils import create_deck_zip, extract_deck_zip, validate_deck_structure
from ..utils.find_replace import convert_remote_urls_to_local
from ..utils.html_to_json import convert_html_to_json, parse_html_deck


class HomePage:
    """Home page component."""
    
    def __init__(self, config: Config):
        self.config = config
        self.status_label: Optional[ui.label] = None
        self.deck_info_card: Optional[ui.card] = None
    
    def render(self):
        """Render the home page."""
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            ui.markdown('# 📊 Slides Editor')
            ui.markdown('*Edit reveal.js decks with Slides.com integration*')
            
            ui.separator()
            
            # Session folder section
            self._render_session_folder_section()
            
            ui.separator()
            
            # Deck operations section
            self._render_deck_operations_section()
            
            ui.separator()
            
            # Status section
            self._render_status_section()
    
    def _render_session_folder_section(self):
        """Render session folder controls."""
        with ui.card().classes('w-full'):
            ui.label('Session Folder').classes('text-h6')
            
            with ui.row().classes('w-full items-center gap-2'):
                session_folder = self.config.session_folder
                folder_text = str(session_folder) if session_folder else "No folder selected"
                
                ui.label(folder_text).classes('flex-grow')
                
                ui.button('Select Folder', on_click=self._select_session_folder, icon='folder')
                
                if session_folder:
                    ui.button('Change', on_click=self._select_session_folder, icon='edit')
                    ui.button(
                        'Open in Explorer',
                        on_click=lambda: self._open_in_explorer(session_folder),
                        icon='launch'
                    )
            
            # Show folder info if selected
            if session_folder and session_folder.exists():
                plots_folder = self.config.get_plots_folder()
                with ui.row().classes('w-full gap-4 mt-2'):
                    ui.label(f'📁 Deck files: {len(list(session_folder.glob("*")))}')
                    if plots_folder:
                        plot_count = len(list(plots_folder.glob('*.html')))
                        ui.label(f'📈 Plot files: {plot_count}')
    
    def _render_deck_operations_section(self):
        """Render deck operation buttons."""
        with ui.card().classes('w-full'):
            ui.label('Deck Operations').classes('text-h6')
            
            session_folder = self.config.session_folder
            deck_id = self.config.deck_id
            
            with ui.column().classes('w-full gap-2'):
                # Convert to JSON button
                convert_btn = ui.button(
                    '🔄 Convert HTML to JSON',
                    on_click=self._convert_to_json,
                    icon='transform'
                ).classes('w-full')
                convert_btn.enabled = session_folder is not None
                
                # Upload button (now uses Define API - no token needed!)
                upload_btn = ui.button(
                    '⬆️ Upload to Slides.com (Opens Browser)',
                    on_click=self._upload_deck,
                    icon='cloud_upload'
                ).classes('w-full')
                upload_btn.enabled = session_folder is not None
                
                ui.label('ℹ️ Upload uses the Define API - you\'ll review the deck in your browser before saving.').classes('text-sm text-grey-7')
                
                # Open in Slides.com button
                if deck_id:
                    ui.button(
                        '🌐 Open Deck in Slides.com Editor',
                        on_click=lambda: ui.navigate.to(f'https://slides.com/editor/{deck_id}'),
                        icon='edit'
                    ).classes('w-full')
                
                # Download button
                download_btn = ui.button(
                    '⬇️ Download Edited Deck',
                    on_click=self._download_deck,
                    icon='cloud_download'
                ).classes('w-full')
                download_btn.enabled = deck_id is not None
                
                # API token setup
                with ui.expansion('API Settings', icon='settings').classes('w-full'):
                    with ui.column().classes('w-full gap-2'):
                        api_token = self.config.slides_api_token or ''
                        token_input = ui.input(
                            'Slides.com API Token',
                            value=api_token,
                            password=True,
                            password_toggle_button=True
                        ).classes('w-full')
                        
                        ui.button(
                            'Save Token',
                            on_click=lambda: self._save_api_token(token_input.value),
                            icon='save'
                        )
                        
                        ui.button(
                            'Test Connection',
                            on_click=self._test_api_connection,
                            icon='network_check'
                        )
    
    def _render_status_section(self):
        """Render status display."""
        with ui.card().classes('w-full'):
            ui.label('Status').classes('text-h6')
            self.status_label = ui.label('Ready').classes('text-grey-7')
            
            if self.config.last_upload_timestamp:
                ui.label(f'Last upload: {self.config.last_upload_timestamp}').classes('text-sm text-grey-6')
    
    async def _select_session_folder(self):
        """Handle ZIP file selection."""
        # Use a text input dialog for browser mode
        with ui.dialog() as dialog, ui.card():
            ui.label('Enter Deck ZIP File Path').classes('text-h6')
            ui.label('Path to your deck ZIP file (contains index.html and data_folder/)')
            
            file_input = ui.input(
                'ZIP File Path',
                placeholder=r'C:\path\to\your\deck.zip'
            ).classes('w-full').props('autofocus')
            
            with ui.row().classes('w-full gap-2'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('Select', on_click=lambda: self._confirm_zip_selection(file_input.value, dialog))
        
        dialog.open()
    
    def _confirm_zip_selection(self, file_path: str, dialog):
        """Confirm and save ZIP file selection."""
        if not file_path:
            ui.notify('Please enter a file path', type='warning')
            return
        
        zip_file = Path(file_path)
        if not zip_file.exists():
            ui.notify('File does not exist', type='negative')
            return
        
        if not zip_file.is_file() or not zip_file.suffix == '.zip':
            ui.notify('File must be a ZIP file', type='negative')
            return
        
        # Save ZIP file path
        self.config.deck_zip_file = zip_file
        
        # Extract ZIP to temporary session folder
        import tempfile
        from ..utils.zip_utils import extract_deck_zip
        
        # Create a persistent temp folder for this session
        temp_base = Path(tempfile.gettempdir()) / "slides_editor"
        temp_base.mkdir(exist_ok=True)
        session_folder = temp_base / zip_file.stem
        
        # Clear and recreate
        import shutil
        if session_folder.exists():
            shutil.rmtree(session_folder)
        
        try:
            extract_deck_zip(zip_file, session_folder)
            self.config.session_folder = session_folder
            self._update_status(f'ZIP extracted to: {session_folder}')
            ui.notify(f'ZIP file selected: {zip_file.name}', type='positive')
            dialog.close()
            
            # Refresh the page to show updated info
            ui.navigate.reload()
        except Exception as e:
            ui.notify(f'Failed to extract ZIP: {str(e)}', type='negative')
    
    def _confirm_folder_selection(self, folder_path: str, dialog):
        """Legacy method - kept for compatibility."""
        if not folder_path:
            ui.notify('Please enter a folder path', type='warning')
            return
        
        folder = Path(folder_path)
        if not folder.exists():
            ui.notify('Folder does not exist', type='negative')
            return
        
        if not folder.is_dir():
            ui.notify('Path is not a directory', type='negative')
            return
        
        self.config.session_folder = folder
        self._update_status(f'Session folder set to: {folder}')
        ui.notify(f'Session folder selected: {folder.name}', type='positive')
        dialog.close()
        
        # Refresh the page to show updated info
        ui.navigate.reload()
    
    def _open_in_explorer(self, folder: Path):
        """Open folder in OS file explorer."""
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            subprocess.Popen(['explorer', str(folder)])
        elif platform.system() == 'Darwin':  # macOS
            subprocess.Popen(['open', str(folder)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(folder)])
    
    async def _upload_deck(self):
        """Upload deck to Slides.com using Define API with HTTPS plot URLs."""
        session_folder = self.config.session_folder
        if not session_folder or not session_folder.exists():
            ui.notify('Please select a ZIP file first', type='negative')
            return
        
        # Find JSON file
        json_files = list(session_folder.glob('*.json'))
        if not json_files:
            ui.notify('Please convert HTML to JSON first (click "Convert HTML to JSON")', type='warning')
            return
        
        json_file = json_files[0]
        
        self._update_status(f'Reading {json_file.name}...')
        
        try:
            import json
            
            # Read the deck JSON
            deck_json = json.loads(json_file.read_text(encoding='utf-8'))
            
            # Transform URLs to use HTTPS localhost (port 8766 by default)
            https_port = self.config.local_server_port + 1
            base_url = f"https://localhost:{https_port}"
            
            self._update_status('Transforming plot URLs to HTTPS...')
            deck_json = self._transform_plot_urls(deck_json, base_url)
            
            self._update_status('Opening Slides.com in browser...')
            
            # Use Define API (opens browser, no auth needed here)
            url = create_deck_via_define_api(deck_json)
            
            self._update_status(f'✅ Plots will be served via {base_url}')
            ui.notify(f'Deck opened in browser! Plots served at {base_url}', type='positive')
            
        except Exception as e:
            self._update_status(f'❌ Upload failed: {str(e)}')
            ui.notify(f'Upload failed: {str(e)}', type='negative')
            import traceback
            traceback.print_exc()
    
    def _transform_plot_urls(self, deck_json: dict, base_url: str) -> dict:
        """Transform local file paths to HTTPS URLs."""
        for slide in deck_json.get('slides', []):
            if isinstance(slide, list):
                # Handle vertical slides
                for sub_slide in slide:
                    self._transform_slide_urls(sub_slide, base_url)
            else:
                self._transform_slide_urls(slide, base_url)
        return deck_json
    
    def _transform_slide_urls(self, slide: dict, base_url: str):
        """Transform URLs in a single slide."""
        for block in slide.get('blocks', []):
            if block.get('type') in ['iframe', 'image'] and 'value' in block:
                old_path = block['value']
                # Convert local path to URL
                if not old_path.startswith('http'):
                    # Remove data folder prefix (e.g., "PANC1_HAPLN1_data/")
                    # since the server serves from that folder as root
                    path_parts = old_path.split('/')
                    if len(path_parts) > 1 and path_parts[0].endswith('_data'):
                        # Remove first part (data folder name)
                        new_path = '/'.join(path_parts[1:])
                    else:
                        new_path = old_path
                    
                    # URL-encode the path to handle special characters like # in filenames
                    # Use safe='/' to preserve path separators
                    encoded_path = quote(new_path, safe='/')
                    block['value'] = f"{base_url}/plots/{encoded_path}"
    
    async def _download_deck(self):
        """Download edited deck from Slides.com."""
        deck_id = self.config.deck_id
        if not deck_id:
            ui.notify('No deck ID available', type='negative')
            return
        
        api_token = self.config.slides_api_token
        if not api_token:
            ui.notify('Please configure API token first', type='negative')
            return
        
        session_folder = self.config.session_folder
        if not session_folder:
            ui.notify('Please select a session folder first', type='negative')
            return
        
        self._update_status('Downloading deck from Slides.com...')
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / 'downloaded_deck.zip'
                
                # Download via API
                async with SlidesAPI(api_token) as api:
                    await api.download_deck(deck_id, zip_path)
                
                self._update_status('Extracting and post-processing...')
                
                # Extract to temporary location
                extract_folder = Path(temp_dir) / 'extracted'
                extract_deck_zip(zip_path, extract_folder)
                
                # Post-process: convert remote URLs back to local
                local_port = self.config.local_server_port
                convert_remote_urls_to_local(
                    extract_folder,
                    'https://slides.com',  # Adjust based on actual Slides.com URLs
                    local_port
                )
                
                # Copy back to session folder
                output_folder = session_folder / f'edited_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                output_folder.mkdir(exist_ok=True)
                
                import shutil
                for item in extract_folder.iterdir():
                    dest = output_folder / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                
                self._update_status(f'✅ Download complete! Saved to: {output_folder.name}')
                ui.notify('Deck downloaded successfully!', type='positive')
        
        except Exception as e:
            self._update_status(f'❌ Download failed: {str(e)}')
            ui.notify(f'Download failed: {str(e)}', type='negative')
    
    def _save_api_token(self, token: str):
        """Save API token to config."""
        self.config.slides_api_token = token
        ui.notify('API token saved', type='positive')
    
    async def _test_api_connection(self):
        """Test API connection."""
        api_token = self.config.slides_api_token
        if not api_token:
            ui.notify('Please configure API token first', type='negative')
            return
        
        self._update_status('Testing API connection...')
        
        try:
            async with SlidesAPI(api_token) as api:
                is_connected = await api.test_connection()
                
                if is_connected:
                    self._update_status('✅ API connection successful')
                    ui.notify('API connection successful!', type='positive')
                else:
                    self._update_status('❌ API connection failed')
                    ui.notify('API connection failed', type='negative')
        
        except Exception as e:
            self._update_status(f'❌ Connection error: {str(e)}')
            ui.notify(f'Connection error: {str(e)}', type='negative')
    
    async def _convert_to_json(self):
        """Convert HTML deck to Slides.com JSON format."""
        session_folder = self.config.session_folder
        if not session_folder or not session_folder.exists():
            ui.notify('Please select a ZIP file first', type='negative')
            return
        
        # Find the main HTML file (index.html or similar)
        html_files = list(session_folder.glob('*.html'))
        if not html_files:
            ui.notify('No HTML file found in session folder', type='negative')
            return
        
        # Use the first HTML file (usually index.html or deck name.html)
        html_file = html_files[0]
        
        self._update_status(f'Converting {html_file.name} to JSON...')
        
        try:
            import json
            
            # Parse HTML to JSON
            deck_json = parse_html_deck(html_file)
            
            # Save JSON file
            json_path = session_folder / f'{html_file.stem}.json'
            json_path.write_text(
                json.dumps(deck_json, indent=2),
                encoding='utf-8'
            )
            
            self._update_status(f'✅ JSON created: {json_path.name}')
            ui.notify(f'Converted to JSON: {json_path.name}', type='positive')
            
            # Show preview dialog
            with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl'):
                ui.label('JSON Preview').classes('text-h6')
                ui.label(f'File: {json_path.name}')
                
                # Show first few slides as preview
                preview = {
                    'title': deck_json.get('title', ''),
                    'total_slides': len(deck_json.get('slides', [])),
                    'dimensions': f"{deck_json.get('width', 960)}x{deck_json.get('height', 700)}",
                    'first_slide_preview': deck_json.get('slides', [{}])[0] if deck_json.get('slides') else {}
                }
                
                ui.code(json.dumps(preview, indent=2), language='json').classes('w-full')
                
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Copy JSON Path', on_click=lambda: self._copy_to_clipboard(str(json_path)))
                    ui.button('Close', on_click=dialog.close)
            
            dialog.open()
            
        except Exception as e:
            self._update_status(f'❌ Conversion failed: {str(e)}')
            ui.notify(f'Conversion failed: {str(e)}', type='negative')
            import traceback
            traceback.print_exc()
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
            ui.notify('Copied to clipboard', type='positive')
        except Exception as e:
            ui.notify(f'Failed to copy: {str(e)}', type='warning')
    
    def _update_status(self, message: str):
        """Update status label."""
        if self.status_label:
            self.status_label.text = message
