"""
Local HTTP server for serving Plotly HTML files.
Provides endpoints to serve plot files from the configured plots folder.
"""
import asyncio
from pathlib import Path
from typing import Optional
from urllib.parse import unquote
from aiohttp import web
import logging

logger = logging.getLogger(__name__)


class PlotServer:
    """HTTP server for serving Plotly HTML files locally."""

    def __init__(self, plots_folder: Path, port: int = 8765):
        self.plots_folder = plots_folder
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._setup_routes()

    def _setup_routes(self):
        """Configure server routes."""
        self.app.router.add_get('/plots/{filename:.+}', self.serve_plot)
        self.app.router.add_get('/plots', self.list_plots)
        self.app.router.add_get('/', self.index)

    async def serve_plot(self, request: web.Request) -> web.Response:
        """Serve a specific plot file (supports subfolders)."""
        filename = request.match_info['filename']
        # Decode URL-encoded filename (e.g., %20 -> space)
        filename = unquote(filename)
        file_path = self.plots_folder / filename

        if not file_path.exists() or not file_path.is_file():
            return web.Response(text="Plot not found", status=404)

        # Security check: ensure file is within plots folder
        try:
            file_path.resolve().relative_to(self.plots_folder.resolve())
        except ValueError:
            return web.Response(text="Invalid path", status=403)

        try:
            # Use FileResponse for efficient streaming with caching
            response = web.FileResponse(path=file_path)
            # Cache for 5 minutes; browser will revalidate via ETag after that
            response.headers['Cache-Control'] = 'public, max-age=300'
            return response
        except Exception as e:
            logger.error(f"Error serving plot {filename}: {e}")
            return web.Response(text="Error serving plot", status=500)

    async def list_plots(self, request: web.Request) -> web.Response:
        """List all available plot files recursively."""
        if not self.plots_folder.exists():
            return web.json_response({"plots": []})

        plots = []
        # Search recursively for HTML and image files
        for file_path in self.plots_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.html', '.png', '.jpg', '.jpeg', '.svg']:
                # Get relative path from plots folder
                rel_path = file_path.relative_to(self.plots_folder)
                plots.append({
                    "name": str(rel_path),
                    "url": f"http://localhost:{self.port}/plots/{rel_path}",
                    "size": file_path.stat().st_size,
                    "type": file_path.suffix[1:]  # Remove the dot
                })

        return web.json_response({"plots": plots})

    async def index(self, request: web.Request) -> web.Response:
        """Serve index page."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Slides Editor - Plot Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .plot-list { margin-top: 20px; }
                .plot-item {
                    padding: 10px;
                    margin: 5px 0;
                    background: #f5f5f5;
                    border-radius: 4px;
                }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>Plot Server Running</h1>
            <p>Server is running on port {port}</p>
            <p><a href="/plots">View available plots (JSON)</a></p>
        </body>
        </html>
        """.format(port=self.port)
        return web.Response(text=html, content_type='text/html')

    async def start(self) -> None:
        """Start the server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()
        logger.info(f"Plot server started on http://localhost:{self.port}")

    async def stop(self) -> None:
        """Stop the server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Plot server stopped")

    def get_plot_url(self, filename: str) -> str:
        """Generate URL for a specific plot file."""
        return f"http://localhost:{self.port}/plots/{filename}"

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.site is not None and self.runner is not None
