"""
Main entry point for slides_editor application.
A NiceGUI-based tool for editing reveal.js slide decks with Slides.com integration.
"""
import asyncio
import logging
from pathlib import Path
from nicegui import ui, app

from app.config import Config
from app.local_server import PlotServer
from app.https_server import HTTPSPlotServer
from app.ui.home import HomePage
from app.ui.plots import PlotsPage
from app.ui.advanced import AdvancedPage


class SessionState:
    """In-memory session state (not persisted)."""
    def __init__(self):
        self.extracted_folder: Path = None  # Main ZIP extraction
        self.user_uploads_folder: Path = None  # Future: user-added files
        self.reveal_slides: list[Path] = []  # Detected reveal.js files
        self.plot_files: list[Path] = []  # Detected plot HTML files
        self.server_running: bool = False  # Server status
    
    def reset(self):
        """Clear session state."""
        self.extracted_folder = None
        self.user_uploads_folder = None
        self.reveal_slides = []
        self.plot_files = []
        # Don't reset server_running - that's independent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress noisy asyncio connection errors on Windows
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


class SlidesEditorApp:
    """Main application class."""
    
    def __init__(self):
        self.config = Config()
        self.session = SessionState()  # In-memory session state
        self.plot_server: PlotServer = None
        self.https_server: HTTPSPlotServer = None
        # Create servers (not started until user clicks Start)
        self._create_servers()
    
    def _create_servers(self):
        """Create the plot server instances (not started yet)."""
        # HTTP server (for local development)
        self.plot_server = PlotServer(
            None,  # No folder initially
            self.config.local_server_port
        )
        # HTTPS server (for Slides.com integration)
        https_port = self.config.local_server_port + 1
        self.https_server = HTTPSPlotServer(
            None,  # No folder initially
            https_port
        )
        logger.info(f"Plot servers created - HTTP: {self.config.local_server_port}, HTTPS: {https_port}")
    
    def update_server_folder(self, folder: Path):
        """Update the folder that servers are serving from."""
        if self.plot_server:
            self.plot_server.plots_folder = folder
        if self.https_server:
            self.https_server.plots_folder = folder
        logger.info(f"Updated server folder to: {folder}")
    
    async def start_plot_server(self):
        """Start the plot servers."""
        if self.session.server_running:
            logger.info("Servers already running")
            return
            
        if self.plot_server:
            try:
                await self.plot_server.start()
                logger.info("HTTP plot server started successfully")
            except Exception as e:
                logger.error(f"Failed to start HTTP plot server: {e}")
        
        if self.https_server:
            try:
                await self.https_server.start()
                logger.info("HTTPS plot server started successfully")
            except Exception as e:
                logger.error(f"Failed to start HTTPS plot server: {e}")
        
        self.session.server_running = True
    
    async def stop_plot_server(self):
        """Stop the plot servers."""
        if not self.session.server_running:
            logger.info("Servers not running")
            return
            
        if self.plot_server:
            try:
                await self.plot_server.stop()
                logger.info("HTTP plot server stopped")
            except Exception as e:
                logger.error(f"Failed to stop HTTP plot server: {e}")
        
        if self.https_server:
            try:
                await self.https_server.stop()
                logger.info("HTTPS plot server stopped")
            except Exception as e:
                logger.error(f"Failed to stop HTTPS plot server: {e}")
        
        self.session.server_running = False
    
    def _render_header(self):
        """Render page header with navigation."""
        with ui.header().classes('items-center justify-between'):
            ui.label('📊 Slides Editor').classes('text-h5')
            
            with ui.row():
                ui.link('Home', '/').classes('text-white')
                ui.link('Plots', '/plots').classes('text-white ml-4')
                ui.link('Advanced', '/advanced').classes('text-white ml-4')
    
    def _render_footer(self):
        """Render page footer with server status."""
        with ui.footer().classes('bg-grey-2'):
            with ui.row().classes('w-full justify-between items-center'):
                server_status = '🟢 Running' if self.plot_server and self.plot_server.is_running() else '🔴 Stopped'
                ui.label(f'Plot Server: {server_status}')
                
                if self.plot_server:
                    ui.label(f'Port: {self.config.local_server_port}')
    
    def setup_ui(self):
        """Set up the UI pages."""
        # Define pages
        @ui.page('/')
        def home_page():
            """Home page route."""
            self._render_header()
            home = HomePage(self.config, self.session, self)
            home.render()
            self._render_footer()
        
        @ui.page('/plots')
        def plots_page():
            """Plots page route."""
            self._render_header()
            plots = PlotsPage(self.config, self.session)
            plots.render()
            self._render_footer()
        
        @ui.page('/advanced')
        def advanced_page():
            """Advanced page route."""
            self._render_header()
            advanced = AdvancedPage(self.config)
            advanced.render()
            self._render_footer()
    
    def run(self, **kwargs):
        """Run the application."""
        # Set up UI
        self.setup_ui()
        
        # Stop servers on shutdown (if running)
        app.on_shutdown(self.stop_plot_server)
        
        # Run NiceGUI app
        ui.run(
            title='Slides Editor',
            favicon='📊',
            **kwargs
        )


def main():
    """Application entry point."""
    editor_app = SlidesEditorApp()
    
    # Run in browser mode (more reliable than native mode)
    # For native window: editor_app.run(native=True, window_size=(1200, 800))
    # For development with auto-reload: editor_app.run(reload=True)
    
    editor_app.run(
        reload=False,
        port=8080
    )


if __name__ == '__main__':
    main()
