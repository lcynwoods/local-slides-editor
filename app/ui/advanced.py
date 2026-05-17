"""
Advanced page UI for slides_editor.
Advanced settings, diagnostics, and configuration options.
"""
from nicegui import ui

from ..config import Config
from ..utils.file_utils import clean_temp_files


class AdvancedPage:
    """Advanced page component."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def render(self):
        """Render the advanced page."""
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            ui.markdown('# Advanced Settings')
            ui.markdown('*Configuration and advanced options*')
            
            ui.separator()
            
            # Server configuration
            self._render_server_config()
            
            ui.separator()
            
            # Configuration reset
            self._render_config_reset()
    
    def _render_server_config(self):
        """Render server configuration."""
        with ui.card().classes('w-full'):
            ui.label('Local Server Configuration').classes('text-h6')
            
            with ui.column().classes('w-full gap-2'):
                # Port configuration
                port_input = ui.number(
                    'Server Port',
                    value=self.config.local_server_port,
                    min=1024,
                    max=65535
                ).classes('w-64')
                
                ui.button(
                    'Update Port',
                    on_click=lambda: self._update_port(int(port_input.value)),
                    icon='save'
                ).props('color=orange')
                
                ui.label('Note: Restart required for port changes to take effect').classes('text-sm text-orange-6')
    
    def _render_config_reset(self):
        """Render configuration reset options."""
        with ui.card().classes('w-full'):
            ui.label('Configuration Reset').classes('text-h6 text-red-6')
            
            with ui.column().classes('w-full gap-2'):
                ui.label('Warning: This will clear all settings').classes('text-orange-6')
                
                ui.button(
                    'Reset All Configuration',
                    on_click=self._confirm_reset,
                    icon='restart_alt'
                ).props('color=red')
                
                # Clean temp files
                ui.separator()
                ui.button(
                    'Clean Temporary Files',
                    on_click=self._clean_temp_files,
                    icon='cleaning_services'
                ).props('color=orange')
    
    def _update_port(self, port: int):
        """Update server port."""
        self.config.local_server_port = port
        ui.notify(f'Server port updated to {port}. Please restart the application.', type='info')
    
    def _confirm_reset(self):
        """Confirm configuration reset."""
        with ui.dialog() as dialog, ui.card():
            ui.label('Confirm Reset').classes('text-h6')
            ui.label('This will clear all settings including:')
            with ui.column().classes('ml-4'):
                ui.label('- Session folder path')
                ui.label('- Deck ID')
                ui.label('- API token')
                ui.label('- All other configuration')
            
            ui.label('Are you sure?').classes('text-orange-6 mt-2')
            
            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button(
                    'Reset',
                    on_click=lambda: [self._reset_config(), dialog.close()],
                    color='red'
                )
        
        dialog.open()
    
    def _reset_config(self):
        """Reset all configuration."""
        self.config.reset()
        ui.notify('Configuration reset. Please restart the application.', type='warning')
    
    def _clean_temp_files(self):
        """Clean temporary files from session folder."""
        session_folder = self.config.session_folder
        if not session_folder or not session_folder.exists():
            ui.notify('No session folder configured', type='warning')
            return
        
        removed = clean_temp_files(session_folder)
        ui.notify(f'Removed {removed} temporary file(s)', type='positive')
    
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
            ui.notify('Copied to clipboard', type='positive')
        except Exception:
            ui.notify(f'Value: {text}', type='info')
