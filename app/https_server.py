"""
HTTPS server for serving plots to Slides.com.
Uses self-signed certificates for local HTTPS serving.
"""
import asyncio
from pathlib import Path
from typing import Optional
from aiohttp import web
import ssl
import logging

logger = logging.getLogger(__name__)


class HTTPSPlotServer:
    """HTTPS server for serving plots with self-signed certificates."""
    
    def __init__(self, plots_folder: Path, port: int = 8766):
        self.plots_folder = plots_folder
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.ssl_context: Optional[ssl.SSLContext] = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Configure server routes."""
        self.app.router.add_get('/plots/{filename:.+}', self.serve_plot)
        self.app.router.add_get('/plots', self.list_plots)
        self.app.router.add_get('/', self.index)
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create a self-signed SSL context using Python's ssl module."""
        import tempfile
        from pathlib import Path
        
        cert_dir = Path(tempfile.gettempdir()) / "slides_editor_certs"
        cert_dir.mkdir(exist_ok=True)
        
        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "key.pem"
        
        # Generate self-signed certificate if it doesn't exist
        if not cert_file.exists() or not key_file.exists():
            logger.info("Generating self-signed certificate...")
            try:
                # Try using cryptography library
                from cryptography import x509
                from cryptography.x509.oid import NameOID
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import rsa
                from cryptography.hazmat.primitives import serialization
                from ipaddress import IPv4Address
                import datetime
                
                # Generate private key
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                )
                
                # Generate certificate
                subject = issuer = x509.Name([
                    x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"State"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, u"City"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SlidesEditor"),
                    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
                ])
                
                cert = x509.CertificateBuilder().subject_name(
                    subject
                ).issuer_name(
                    issuer
                ).public_key(
                    private_key.public_key()
                ).serial_number(
                    x509.random_serial_number()
                ).not_valid_before(
                    datetime.datetime.utcnow()
                ).not_valid_after(
                    datetime.datetime.utcnow() + datetime.timedelta(days=365)
                ).add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName(u"localhost"),
                        x509.IPAddress(IPv4Address("127.0.0.1")),
                    ]),
                    critical=False,
                ).sign(private_key, hashes.SHA256())
                
                # Write private key
                with open(key_file, "wb") as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                # Write certificate
                with open(cert_file, "wb") as f:
                    f.write(cert.public_bytes(serialization.Encoding.PEM))
                
                logger.info(f"Generated self-signed certificate at {cert_file}")
                
            except ImportError:
                logger.warning("cryptography library not available, creating basic SSL context")
                # Create a very basic unverified SSL context
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                return context
            except Exception as e:
                logger.error(f"Failed to generate certificate: {e}")
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                return context
        
        # Load certificate
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(cert_file, key_file)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context
        except Exception as e:
            logger.error(f"Failed to load certificate: {e}")
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
    
    async def serve_plot(self, request: web.Request) -> web.Response:
        """Serve a specific plot file (supports subfolders)."""
        filename = request.match_info['filename']
        file_path = self.plots_folder / filename
        
        if not file_path.exists() or not file_path.is_file():
            return web.Response(text="Plot not found", status=404)
        
        # Security check
        try:
            file_path.resolve().relative_to(self.plots_folder.resolve())
        except ValueError:
            return web.Response(text="Invalid path", status=403)
        
        # Determine content type
        content_type = 'text/html'
        if filename.endswith('.png'):
            content_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.endswith('.svg'):
            content_type = 'image/svg+xml'
        
        # Add CORS headers for Slides.com
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': '*'
        }
        
        try:
            if content_type.startswith('image/'):
                with open(file_path, 'rb') as f:
                    content = f.read()
                return web.Response(body=content, content_type=content_type, headers=headers)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return web.Response(text=content, content_type=content_type, headers=headers)
        except Exception as e:
            logger.error(f"Error serving plot {filename}: {e}")
            return web.Response(text="Error serving plot", status=500)
    
    async def list_plots(self, request: web.Request) -> web.Response:
        """List all available plot files."""
        if not self.plots_folder.exists():
            return web.json_response({"plots": []})
        
        plots = []
        for file_path in self.plots_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.html', '.png', '.jpg', '.jpeg', '.svg']:
                rel_path = file_path.relative_to(self.plots_folder)
                plots.append({
                    "name": str(rel_path),
                    "url": f"https://localhost:{self.port}/plots/{rel_path}",
                    "size": file_path.stat().st_size,
                    "type": file_path.suffix[1:]
                })
        
        return web.json_response({"plots": plots})
    
    async def index(self, request: web.Request) -> web.Response:
        """Serve index page."""
        return web.Response(text=f"HTTPS Plot Server running on port {self.port}", content_type='text/html')
    
    async def start(self):
        """Start the HTTPS server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Create SSL context
        self.ssl_context = self._create_ssl_context()
        
        self.site = web.TCPSite(
            self.runner,
            'localhost',
            self.port,
            ssl_context=self.ssl_context
        )
        await self.site.start()
        logger.info(f"HTTPS Plot server started on https://localhost:{self.port}")
    
    async def stop(self):
        """Stop the HTTPS server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("HTTPS Plot server stopped")
