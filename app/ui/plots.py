"""
Plots page UI for slides_editor.
Lists and manages Plotly HTML files with click-to-copy URLs.
"""
from nicegui import ui, app
from pathlib import Path
from typing import Optional, List
from urllib.parse import quote
import pyperclip

from ..config import Config
from ..utils.file_utils import get_plot_files


class PlotsPage:
    """Plots page component."""
    
    def __init__(self, config: Config, session=None):
        self.config = config
        self.session = session
        self.search_term: str = ''
        self.plot_container: Optional[ui.column] = None
    
    def render(self):
        """Render the plots page."""
        with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
            ui.markdown('# 📈 Plot Files')
            ui.markdown('*Click any plot to copy its iframe URL*')
            
            ui.separator()
            
            # Search and controls
            self._render_controls()
            
            ui.separator()
            
            # Plot list
            self.plot_container = ui.column().classes('w-full gap-2')
            self._render_plot_list()
    
    def _render_controls(self):
        """Render search and control buttons."""
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full items-center gap-2'):
                # Search input
                search_input = ui.input(
                    'Search plots',
                    placeholder='Filter by filename...'
                ).classes('flex-grow')
                search_input.on('input', lambda e: self._search_plots(e.value))
                
                # Refresh button
                ui.button('Refresh', on_click=self._render_plot_list, icon='refresh')
                
                # Open plots folder button
                plots_folder = self.session.extracted_folder if self.session else None
                if plots_folder:
                    ui.button(
                        'Open Folder',
                        on_click=lambda: self._open_in_explorer(plots_folder),
                        icon='folder_open'
                    )
            
            # Manual URL generator
            with ui.expansion('Manual URL Generator', icon='link').classes('w-full mt-2'):
                with ui.row().classes('w-full items-center gap-2'):
                    filename_input = ui.input(
                        'Plot filename',
                        placeholder='example_plot.html'
                    ).classes('flex-grow')
                    
                    ui.button(
                        'Generate & Copy URL',
                        on_click=lambda: self._copy_manual_url(filename_input.value),
                        icon='content_copy'
                    )
    
    def _render_plot_list(self):
        """Render list of plot files."""
        if not self.plot_container:
            return
        
        self.plot_container.clear()
        
        plots_folder = self.session.extracted_folder if self.session else None
        
        if not plots_folder:
            with self.plot_container:
                ui.label('ℹ️ Upload a ZIP file on the Home page to see plots here.')
            return
        
        plot_files = get_plot_files(plots_folder)
        
        if not plot_files:
            with self.plot_container:
                ui.label(f'No plot files found in: {plots_folder}')
            return
        
        # Filter by search term
        if self.search_term:
            plot_files = [
                f for f in plot_files
                if self.search_term.lower() in f.name.lower()
            ]
        
        with self.plot_container:
            ui.label(f'Found {len(plot_files)} plot file(s)').classes('text-grey-7 mb-2')
            
            for plot_file in plot_files:
                self._render_plot_card(plot_file)
    
    def _render_plot_card(self, plot_file: Path):
        """Render a single plot file card."""
        plots_folder = self.session.extracted_folder if self.session else None
        
        if not plots_folder:
            return
        
        # Get relative path from plots folder
        relative_path = plot_file.relative_to(plots_folder)
        
        # Use HTTPS URL (port + 1) for Slides.com compatibility
        local_port = self.config.local_server_port
        https_port = local_port + 1
        # URL-encode path to handle special characters like # in filenames
        encoded_path = quote(str(relative_path).replace('\\', '/'), safe='/')
        plot_url = f'https://localhost:{https_port}/plots/{encoded_path}'
        iframe_code = f'<iframe src="{plot_url}" width="100%" height="500"></iframe>'
        
        with ui.card().classes('w-full cursor-pointer hover:bg-grey-2').on(
            'click',
            lambda: self._copy_url(iframe_code, plot_file.name)
        ):
            with ui.row().classes('w-full items-center gap-4'):
                # Icon
                ui.icon('insert_chart', size='lg').classes('text-blue-5')
                
                # File info
                with ui.column().classes('flex-grow'):
                    ui.label(plot_file.name).classes('font-bold')
                    ui.label(plot_url).classes('text-sm text-grey-6')
                    
                    # File size
                    size_kb = plot_file.stat().st_size / 1024
                    ui.label(f'{size_kb:.1f} KB').classes('text-xs text-grey-5')
                
                # Action buttons
                with ui.row().classes('gap-2'):
                    ui.button(
                        icon='content_copy',
                        on_click=lambda: self._copy_url(iframe_code, plot_file.name)
                    ).props('flat round')
                    
                    ui.button(
                        icon='open_in_browser',
                        on_click=lambda p=plot_url: ui.navigate.to(p, new_tab=True)
                    ).props('flat round')
                    
                    ui.button(
                        icon='code',
                        on_click=lambda: self._show_iframe_dialog(iframe_code, plot_file.name)
                    ).props('flat round')
    
    def _copy_url(self, iframe_code: str, filename: str):
        """Copy iframe URL to clipboard."""
        try:
            pyperclip.copy(iframe_code)
            ui.notify(f'Copied iframe code for {filename}!', type='positive')
        except Exception as e:
            # Fallback if pyperclip fails
            ui.notify(f'URL: {iframe_code}', type='info', position='top')
    
    def _copy_manual_url(self, filename: str):
        """Generate and copy URL for manually entered filename."""
        if not filename:
            ui.notify('Please enter a filename', type='warning')
            return
        
        # Ensure .html extension
        if not filename.endswith('.html'):
            filename += '.html'
        
        local_port = self.config.local_server_port
        plot_url = f'http://localhost:{local_port}/plots/{filename}'
        iframe_code = f'<iframe src="{plot_url}" width="100%" height="500"></iframe>'
        
        try:
            pyperclip.copy(iframe_code)
            ui.notify(f'Copied iframe code for {filename}!', type='positive')
        except Exception:
            ui.notify(f'URL: {iframe_code}', type='info', position='top')
    
    def _show_iframe_dialog(self, iframe_code: str, filename: str):
        """Show dialog with full iframe code."""
        with ui.dialog() as dialog, ui.card():
            ui.markdown(f'### Iframe Code for `{filename}`')
            
            code_area = ui.textarea(value=iframe_code).classes('w-full font-mono')
            code_area.props('readonly rows=4')
            
            with ui.row().classes('w-full gap-2'):
                ui.button('Copy', on_click=lambda: self._copy_url(iframe_code, filename))
                ui.button('Close', on_click=dialog.close)
        
        dialog.open()
    
    def _search_plots(self, term: str):
        """Handle search input."""
        self.search_term = term
        self._render_plot_list()
    
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
