"""
Simplified home page for ZIP-based workflow with auto-server.
"""
from nicegui import ui
from pathlib import Path
from typing import Optional, List
from urllib.parse import quote
import tempfile
import logging

from ..config import Config
from ..slides_api import create_deck_via_define_api
from ..utils.zip_utils import extract_deck_zip
from ..utils.reveal_detector import find_html_files
from ..utils.html_to_json import parse_html_deck

logger = logging.getLogger(__name__)


class HomePageSimplified:
    """Simplified home page component."""
    
    def __init__(self, config: Config, app_instance):
        self.config = config
        self.app_instance = app_instance
        self.status_label: Optional[ui.label] = None
        self.file_info_container: Optional[ui.column] = None
        self.reveal_slides: List[Path] = []
        self.plot_files: List[Path] = []
        self.main_container: Optional[ui.column] = None
    
    def render(self):
        """Render the home page."""
        # Clear container if it exists (for re-renders)
        if self.main_container is not None:
            self.main_container.clear()
            with self.main_container:
                self._render_content()
        else:
            self.main_container = ui.column().classes('w-full max-w-4xl mx-auto p-4')
            with self.main_container:
                self._render_content()
    
    def _render_content(self):
        """Render the actual content."""
        ui.markdown('# 📊 Slides Editor')
        ui.markdown('*Auto-serve plots from reveal.js ZIP files*')
        
        ui.separator()
        
        # Server status section
        self._render_server_section()
        
        ui.separator()
        
        # ZIP file selection
        self._render_zip_section()
        
        ui.separator()
        
        # File info (reveal slides + plots)
        with ui.card().classes('w-full') as self.file_info_container:
            ui.label('Detected Files').classes('text-h6')
            self._update_file_info()
        
        ui.separator()
        
        # Upload section
        self._render_upload_section()
        
        ui.separator()
        
        # Status
        with ui.card().classes('w-full'):
            ui.label('Status').classes('text-h6')
            self.status_label = ui.label('Ready.').classes('text-grey-7')
    
    def _render_server_section(self):
        """Render server controls."""
        with ui.card().classes('w-full'):
            ui.label('Plot Server').classes('text-h6')
            
            with ui.row().classes('w-full items-center gap-2'):
                server_running = self.config.server_running
                status_text = '🟢 Running' if server_running else '🔴 Stopped'
                status_color = 'positive' if server_running else 'negative'
                
                ui.badge(status_text, color=status_color)
                
                if server_running:
                    local_port = self.config.local_server_port
                    https_port = local_port + 1
                    ui.label(f'HTTP: localhost:{local_port} | HTTPS: localhost:{https_port}').classes('text-grey-7')
                
                ui.space()
                
                if not server_running:
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
        """Render ZIP file selection."""
        with ui.card().classes('w-full'):
            ui.label('Deck ZIP File').classes('text-h6')
            
            zip_file = self.config.deck_zip_file
            
            with ui.row().classes('w-full items-center gap-2'):
                if zip_file:
                    ui.label(f'📦 {zip_file.name}').classes('flex-grow')
                else:
                    ui.label('No ZIP file selected').classes('flex-grow text-grey-7')
                
                # File upload button
                ui.upload(
                    label='Select ZIP' if not zip_file else 'Change',
                    on_upload=self._handle_zip_upload,
                    auto_upload=True,
                    multiple=False
                ).props('accept=".zip"').classes('ml-auto')
    
    def _render_upload_section(self):
        """Render upload controls."""
        with ui.card().classes('w-full'):
            ui.label('Upload to Slides.com').classes('text-h6')
            
            has_reveal_slides = len(self.reveal_slides) > 0
            server_running = self.config.server_running
            
            upload_btn = ui.button(
                '⬆️ Create Deck (Opens Browser)',
                on_click=self._upload_deck,
                icon='cloud_upload',
                color='primary'
            ).classes('w-full')
            upload_btn.enabled = has_reveal_slides and server_running
            
            if not server_running:
                ui.label('⚠️ Start server before uploading').classes('text-orange-7')
            elif not has_reveal_slides:
                ui.label('⚠️ Select a ZIP file with reveal.js slides').classes('text-orange-7')
    
    def _update_file_info(self):
        """Update the file information display."""
        self.file_info_container.clear()
        
        with self.file_info_container:
            ui.label('Detected Files').classes('text-h6')
            
            if not self.reveal_slides and not self.plot_files:
                ui.label('No files detected - select a ZIP file above').classes('text-grey-7')
                return
            
            # Reveal slides
            if self.reveal_slides:
                ui.label(f'✅ Found {len(self.reveal_slides)} reveal.js slide deck(s):').classes('text-green-7 font-bold')
                for slide_file in self.reveal_slides:
                    extracted_folder = self.config.extracted_folder
                    if extracted_folder:
                        rel_path = slide_file.relative_to(extracted_folder)
                        ui.label(f'  📄 {rel_path}').classes('ml-4 text-sm')
            else:
                ui.label('⚠️ No reveal.js slides found').classes('text-orange-7')
            
            ui.space()
            
            # Plot files
            if self.plot_files:
                ui.label(f'📊 Found {len(self.plot_files)} plot HTML file(s)').classes('text-blue-7')
                ui.label('These will be served via HTTPS for embedding in slides').classes('text-sm text-grey-7')
            else:
                ui.label('ℹ️ No additional HTML files found').classes('text-grey-7')
    
    async def _handle_zip_upload(self, e):
        """Handle ZIP file upload."""
        from zipfile import ZipFile, BadZipFile
        
        try:
            # NiceGUI UploadEventArguments.file has:
            # - name property
            # - read() async method for content
            filename = e.file.name
            
            # Save uploaded file to temp
            temp_zip = Path(tempfile.gettempdir()) / filename
            temp_zip.write_bytes(await e.file.read())
            
            # Validate it's a ZIP
            try:
                with ZipFile(temp_zip, 'r'):
                    pass
            except BadZipFile:
                ui.notify('Invalid ZIP file', type='negative')
                temp_zip.unlink()
                return
            
            self._update_status(f'Extracting {temp_zip.name}...')
            
            # Extract to temp folder
            extract_folder = Path(tempfile.gettempdir()) / 'slides_editor' / temp_zip.stem
            extract_folder.mkdir(parents=True, exist_ok=True)
            
            extract_deck_zip(temp_zip, extract_folder)
            
            # Save config
            self.config.deck_zip_file = temp_zip
            self.config.extracted_folder = extract_folder
            
            # Find HTML files
            self.reveal_slides, self.plot_files = find_html_files(extract_folder)
            
            # Update server folder
            self.app_instance.update_server_folder(extract_folder)
            
            # Update UI
            self._update_file_info()
            ui.notify(f'Extracted {temp_zip.name}', type='positive')
            
            if self.reveal_slides:
                ui.notify(f'Found {len(self.reveal_slides)} reveal.js slide deck(s)!', type='positive')
            else:
                ui.notify('No reveal.js slides detected', type='warning')
            
            self._update_status('Ready')
            self.render()
            
        except Exception as e:
            logger.error(f'Error uploading ZIP: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error uploading ZIP')
    
    async def _start_server(self):
        """Start the plot server."""
        try:
            await self.app_instance.start_plot_server()
            ui.notify('Servers started', type='positive')
            self.render()  # Refresh UI
        except Exception as e:
            logger.error(f'Error starting servers: {e}', exc_info=True)
            ui.notify(f'Error starting servers: {e}', type='negative')
    
    async def _stop_server(self):
        """Stop the plot server."""
        try:
            await self.app_instance.stop_plot_server()
            ui.notify('Servers stopped', type='warning')
            self.render()  # Refresh UI
        except Exception as e:
            logger.error(f'Error stopping servers: {e}', exc_info=True)
            ui.notify(f'Error stopping servers: {e}', type='negative')
    
    async def _upload_deck(self):
        """Upload deck to Slides.com via Define API."""
        if not self.reveal_slides:
            ui.notify('No reveal.js slides to upload', type='negative')
            return
        
        if not self.config.server_running:
            ui.notify('Start server before uploading', type='negative')
            return
        
        try:
            # Use first reveal.js file found
            html_file = self.reveal_slides[0]
            
            self._update_status(f'Converting {html_file.name} to JSON...')
            
            # Parse HTML to JSON
            deck_json = parse_html_deck(html_file)
            
            # Transform plot URLs to HTTPS
            https_port = self.config.local_server_port + 1
            base_url = f"https://localhost:{https_port}"
            deck_json = self._transform_plot_urls(deck_json, base_url)
            
            self._update_status('Opening browser for Slides.com Define API...')
            
            # Upload via Define API (opens browser)
            create_deck_via_define_api(deck_json)
            
            ui.notify('Deck opened in browser! Plots served at ' + base_url, type='positive')
            self._update_status(f'✅ Deck opened in browser. Plots served at {base_url}')
            
        except Exception as e:
            logger.error(f'Error uploading deck: {e}', exc_info=True)
            ui.notify(f'Error: {e}', type='negative')
            self._update_status('Error uploading deck')
    
    def _transform_plot_urls(self, deck_json: dict, base_url: str) -> dict:
        """Transform plot URLs to use local HTTPS server."""
        for slide in deck_json.get('slides', []):
            if isinstance(slide, list):
                for sub_slide in slide:
                    self._transform_slide_urls(sub_slide, base_url)
            else:
                self._transform_slide_urls(slide, base_url)
        return deck_json
    
    def _transform_slide_urls(self, slide: dict, base_url: str):
        """Transform URLs in a single slide."""
        extracted_folder = self.config.extracted_folder
        if not extracted_folder:
            return
        
        for block in slide.get('blocks', []):
            if block.get('type') in ['iframe', 'image'] and 'value' in block:
                old_path = block['value']
                # Convert local path to URL
                if not old_path.startswith('http'):
                    # Make relative to extracted folder
                    try:
                        # URL-encode the path to handle special characters like # in filenames
                        # Use safe='/' to preserve path separators
                        encoded_path = quote(old_path, safe='/')
                        block['value'] = f"{base_url}/plots/{encoded_path}"
                    except Exception as e:
                        logger.warning(f"Could not transform URL {old_path}: {e}")
    
    def _update_status(self, message: str):
        """Update status label."""
        if self.status_label:
            self.status_label.text = message
