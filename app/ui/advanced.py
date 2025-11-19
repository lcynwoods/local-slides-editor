"""
Advanced page UI for slides_editor.
Advanced settings, diagnostics, and configuration options.
"""
from nicegui import ui
from pathlib import Path
from typing import Optional
import asyncio

from ..config import Config
from ..slides_api import SlidesAPI
from ..utils.file_utils import get_folder_size, format_file_size, clean_temp_files


class AdvancedPage:
    """Advanced page component."""
    
    def __init__(self, config: Config):
        self.config = config
        self.diagnostics_output: Optional[ui.textarea] = None
    
    def render(self):
        """Render the advanced page."""
        with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
            ui.markdown('# ⚙️ Advanced Settings')
            ui.markdown('*Configuration, diagnostics, and advanced options*')
            
            ui.separator()
            
            # Deck management
            self._render_deck_management()
            
            ui.separator()
            
            # Server configuration
            self._render_server_config()
            
            ui.separator()
            
            # Diagnostics
            self._render_diagnostics()
            
            ui.separator()
            
            # Configuration reset
            self._render_config_reset()
    
    def _render_deck_management(self):
        """Render deck management options."""
        with ui.card().classes('w-full'):
            ui.label('Deck Management').classes('text-h6')
            
            with ui.column().classes('w-full gap-2'):
                # Force re-upload
                ui.button(
                    'Force Re-upload Deck (Create New)',
                    on_click=self._force_reupload,
                    icon='cloud_upload'
                ).props('color=orange')
                ui.label('Creates a new deck instead of updating existing').classes('text-sm text-grey-6')
                
                # Current deck ID
                if self.config.deck_id:
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Current Deck ID:').classes('font-bold')
                        ui.label(self.config.deck_id).classes('font-mono')
                        ui.button(
                            icon='content_copy',
                            on_click=lambda: self._copy_to_clipboard(self.config.deck_id)
                        ).props('flat dense')
                
                # Clear deck ID
                ui.button(
                    'Clear Deck ID',
                    on_click=self._clear_deck_id,
                    icon='clear'
                ).props('flat')
    
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
                )
                
                ui.label('Note: Restart required for port changes to take effect').classes('text-sm text-orange-6')
    
    def _render_diagnostics(self):
        """Render diagnostics section."""
        with ui.card().classes('w-full'):
            ui.label('Diagnostics').classes('text-h6')
            
            with ui.column().classes('w-full gap-2'):
                ui.button(
                    'Run Diagnostics',
                    on_click=self._run_diagnostics,
                    icon='bug_report'
                )
                
                self.diagnostics_output = ui.textarea().classes('w-full font-mono text-sm')
                self.diagnostics_output.props('readonly rows=15')
    
    def _render_config_reset(self):
        """Render configuration reset options."""
        with ui.card().classes('w-full'):
            ui.label('Configuration Reset').classes('text-h6 text-red-6')
            
            with ui.column().classes('w-full gap-2'):
                ui.label('⚠️ Warning: This will clear all settings').classes('text-orange-6')
                
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
                )
    
    def _force_reupload(self):
        """Force re-upload by clearing deck ID."""
        self.config.deck_id = None
        ui.notify('Deck ID cleared. Next upload will create a new deck.', type='info')
    
    def _clear_deck_id(self):
        """Clear the deck ID."""
        self.config.deck_id = None
        ui.notify('Deck ID cleared', type='info')
    
    def _update_port(self, port: int):
        """Update server port."""
        self.config.local_server_port = port
        ui.notify(f'Server port updated to {port}. Please restart the application.', type='info')
    
    async def _run_diagnostics(self):
        """Run system diagnostics."""
        if not self.diagnostics_output:
            return
        
        output = []
        output.append('=== SLIDES EDITOR DIAGNOSTICS ===\n')
        
        # Config file location
        output.append(f'Config file: {self.config.config_file}')
        output.append(f'Config exists: {self.config.config_file.exists()}\n')
        
        # Session folder
        session_folder = self.config.session_folder
        output.append(f'Session folder: {session_folder}')
        if session_folder and session_folder.exists():
            size = get_folder_size(session_folder)
            output.append(f'Session folder size: {format_file_size(size)}')
            output.append(f'Files in session folder: {len(list(session_folder.rglob("*")))}')
        else:
            output.append('Session folder not set or does not exist')
        output.append('')
        
        # Plots folder
        plots_folder = self.config.get_plots_folder()
        output.append(f'Plots folder: {plots_folder}')
        if plots_folder and plots_folder.exists():
            plot_files = list(plots_folder.glob('*.html'))
            output.append(f'Plot files: {len(plot_files)}')
            for pf in plot_files[:5]:  # Show first 5
                output.append(f'  - {pf.name}')
            if len(plot_files) > 5:
                output.append(f'  ... and {len(plot_files) - 5} more')
        else:
            output.append('Plots folder not found')
        output.append('')
        
        # API configuration
        output.append(f'Deck ID: {self.config.deck_id or "Not set"}')
        output.append(f'API token configured: {bool(self.config.slides_api_token)}')
        output.append(f'Local server port: {self.config.local_server_port}')
        output.append(f'Last upload: {self.config.last_upload_timestamp or "Never"}\n')
        
        # API connection test
        if self.config.slides_api_token:
            output.append('Testing API connection...')
            try:
                async with SlidesAPI(self.config.slides_api_token) as api:
                    is_connected = await api.test_connection()
                    if is_connected:
                        output.append('✅ API connection: SUCCESS')
                    else:
                        output.append('❌ API connection: FAILED')
            except Exception as e:
                output.append(f'❌ API connection error: {str(e)}')
        else:
            output.append('⚠️ API token not configured')
        
        output.append('\n=== END DIAGNOSTICS ===')
        
        self.diagnostics_output.value = '\n'.join(output)
    
    def _confirm_reset(self):
        """Confirm configuration reset."""
        with ui.dialog() as dialog, ui.card():
            ui.label('⚠️ Confirm Reset').classes('text-h6')
            ui.label('This will clear all settings including:')
            with ui.column().classes('ml-4'):
                ui.label('• Session folder path')
                ui.label('• Deck ID')
                ui.label('• API token')
                ui.label('• All other configuration')
            
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
