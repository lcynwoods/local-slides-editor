"""
Slides.com API integration.
Handles authentication, deck upload, download, and asset management.
"""
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from datetime import datetime
import webbrowser
import urllib.parse

logger = logging.getLogger(__name__)


class SlidesAPIError(Exception):
    """Custom exception for Slides.com API errors."""
    pass


class SlidesAPI:
    """
    Interface to Slides.com API (beta).
    
    Note: Slides.com API documentation may be limited. This implementation
    follows common REST API patterns and may need adjustment based on
    actual API specifications.
    """
    
    BASE_URL = "https://slides.com/api/v1"
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        if not self.session:
            raise SlidesAPIError("API session not initialized. Use async context manager.")
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise SlidesAPIError(
                        f"API request failed: {response.status} - {error_text}"
                    )
                
                return await response.json()
        except aiohttp.ClientError as e:
            raise SlidesAPIError(f"Network error: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Test API connection and authentication."""
        try:
            # Attempt to get user info or deck list
            await self._request("GET", "/user")
            return True
        except SlidesAPIError:
            return False
    
    async def upload_deck(self, zip_path: Path, deck_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a reveal.js deck (as ZIP) to Slides.com.
        
        Args:
            zip_path: Path to the ZIP file containing the reveal.js deck
            deck_id: Optional existing deck ID to update
        
        Returns:
            Dictionary containing deck_id and edit_url
        """
        if not zip_path.exists():
            raise SlidesAPIError(f"Zip file not found: {zip_path}")
        
        # Prepare multipart form data
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        
        form = aiohttp.FormData()
        form.add_field('file', zip_data, filename=zip_path.name, 
                       content_type='application/zip')
        
        # If deck_id exists, update; otherwise create new
        if deck_id:
            endpoint = f"/decks/{deck_id}/import"
            method = "PUT"
        else:
            endpoint = "/decks/import"
            method = "POST"
        
        # Override content-type for multipart
        if self.session:
            headers = dict(self.session.headers)
            headers.pop('Content-Type', None)
            
            result = await self._request(method, endpoint, data=form, headers=headers)
        else:
            raise SlidesAPIError("Session not initialized")
        
        logger.info(f"Deck uploaded successfully. ID: {result.get('id')}")
        return {
            "deck_id": result.get("id"),
            "edit_url": result.get("url"),
            "timestamp": datetime.now().isoformat()
        }
    
    async def download_deck(self, deck_id: str, output_path: Path) -> Path:
        """
        Download an edited deck from Slides.com.
        
        Args:
            deck_id: The deck ID to download
            output_path: Path where the ZIP file should be saved
        
        Returns:
            Path to the downloaded ZIP file
        """
        endpoint = f"/decks/{deck_id}/export"
        
        if not self.session:
            raise SlidesAPIError("Session not initialized")
        
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.get(url) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise SlidesAPIError(
                        f"Download failed: {response.status} - {error_text}"
                    )
                
                # Save ZIP file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                
                logger.info(f"Deck downloaded to: {output_path}")
                return output_path
        
        except aiohttp.ClientError as e:
            raise SlidesAPIError(f"Download error: {str(e)}")
    
    async def upload_asset(self, file_path: Path, deck_id: str) -> Dict[str, Any]:
        """
        Upload an additional asset to a deck's asset library.
        
        Args:
            file_path: Path to the file to upload
            deck_id: The deck ID to upload to
        
        Returns:
            Asset information including URL
        """
        if not file_path.exists():
            raise SlidesAPIError(f"Asset file not found: {file_path}")
        
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        form = aiohttp.FormData()
        form.add_field('file', file_data, filename=file_path.name)
        
        if self.session:
            headers = dict(self.session.headers)
            headers.pop('Content-Type', None)
            
            result = await self._request(
                "POST", 
                f"/decks/{deck_id}/assets",
                data=form,
                headers=headers
            )
        else:
            raise SlidesAPIError("Session not initialized")
        
        logger.info(f"Asset uploaded: {file_path.name}")
        return result
    
    async def get_deck_info(self, deck_id: str) -> Dict[str, Any]:
        """Get information about a specific deck."""
        return await self._request("GET", f"/decks/{deck_id}")
    
    async def list_decks(self) -> list[Dict[str, Any]]:
        """List all user's decks."""
        result = await self._request("GET", "/decks")
        return result.get("decks", [])


def create_deck_via_define_api(deck_json: Dict[str, Any]) -> str:
    """
    Create a deck using the Slides.com Define API (no authentication required).
    
    This opens a browser window where the user will be prompted to sign in
    (if not already) and confirm saving the deck to their account.
    
    Args:
        deck_json: The deck definition in Slides.com JSON format
        
    Returns:
        URL that was opened in the browser
    """
    import json
    import html
    
    # The Define API URL
    define_url = "https://slides.com/decks/define"
    
    # Convert JSON to string and URL-encode it
    json_str = json.dumps(deck_json)
    
    # Create an HTML form that auto-submits
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Creating Slides.com Deck...</title>
    </head>
    <body>
        <h2>Creating your presentation on Slides.com...</h2>
        <p>You will be redirected to Slides.com to review and save your deck.</p>
        <form id="defineForm" action="{define_url}" method="POST">
            <input type="hidden" name="definition" value="{html.escape(json_str)}">
        </form>
        <script>
            // Auto-submit the form
            document.getElementById('defineForm').submit();
        </script>
    </body>
    </html>
    """
    
    # Save to a temporary HTML file and open it
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_file = f.name
    
    # Open in default browser
    webbrowser.open('file://' + temp_file)
    
    logger.info(f"Opened Define API form in browser")
    return f"file://{temp_file}"

