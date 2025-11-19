"""
Configuration management for slides_editor.
Handles persistent storage of user settings and session data.
"""
import json
from pathlib import Path
from typing import Optional
import appdirs

APP_NAME = "slides_editor"
APP_AUTHOR = "lwoods"


class Config:
    """Manages application configuration with persistent storage."""
    
    def __init__(self):
        self.config_dir = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
    
    def _load(self) -> dict:
        """Load configuration from disk."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_config()
        return self._default_config()
    
    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            "deck_zip_file": None,
            "extracted_folder": None,
            "deck_id": None,
            "slides_api_token": None,
            "local_server_port": 8765,
            "server_running": False,
            "last_upload_timestamp": None
        }
    
    def save(self) -> None:
        """Save configuration to disk."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2)
    
    @property
    def extracted_folder(self) -> Optional[Path]:
        """Get the extracted ZIP folder path."""
        folder = self._data.get("extracted_folder")
        return Path(folder) if folder else None
    
    @extracted_folder.setter
    def extracted_folder(self, path: Optional[Path]) -> None:
        """Set the extracted ZIP folder path."""
        self._data["extracted_folder"] = str(path) if path else None
        self.save()
    
    @property
    def session_folder(self) -> Optional[Path]:
        """Get the session folder path."""
        folder_str = self._data.get("session_folder")
        return Path(folder_str) if folder_str else None
    
    @session_folder.setter
    def session_folder(self, value: Optional[Path]) -> None:
        """Set the session folder path."""
        self._data["session_folder"] = str(value) if value else None
        self.save()
    
    @property
    def server_running(self) -> bool:
        """Get server running status."""
        return self._data.get("server_running", False)
    
    @server_running.setter
    def server_running(self, value: bool) -> None:
        """Set server running status."""
        self._data["server_running"] = value
        self.save()
    
    @property
    def deck_id(self) -> Optional[str]:
        """Get the current deck ID."""
        return self._data.get("deck_id")
    
    @deck_id.setter
    def deck_id(self, value: Optional[str]) -> None:
        """Set the current deck ID."""
        self._data["deck_id"] = value
        self.save()
    
    @property
    def slides_api_token(self) -> Optional[str]:
        """Get the Slides.com API token."""
        return self._data.get("slides_api_token")
    
    @slides_api_token.setter
    def slides_api_token(self, value: Optional[str]) -> None:
        """Set the Slides.com API token."""
        self._data["slides_api_token"] = value
        self.save()
    
    @property
    def local_server_port(self) -> int:
        """Get the local server port."""
        return self._data.get("local_server_port", 8765)
    
    @local_server_port.setter
    def local_server_port(self, value: int) -> None:
        """Set the local server port."""
        self._data["local_server_port"] = value
        self.save()
    
    @property
    def last_upload_timestamp(self) -> Optional[str]:
        """Get the last upload timestamp."""
        return self._data.get("last_upload_timestamp")
    
    @last_upload_timestamp.setter
    def last_upload_timestamp(self, value: Optional[str]) -> None:
        """Set the last upload timestamp."""
        self._data["last_upload_timestamp"] = value
        self.save()
    
    @property
    def deck_zip_file(self) -> Optional[Path]:
        """Get the deck ZIP file path."""
        zip_file = self._data.get("deck_zip_file")
        return Path(zip_file) if zip_file else None
    
    @deck_zip_file.setter
    def deck_zip_file(self, value: Optional[Path]) -> None:
        """Set the deck ZIP file path."""
        self._data["deck_zip_file"] = str(value) if value else None
        self.save()
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._data = self._default_config()
        self.save()
    
    def get_plots_folder(self) -> Optional[Path]:
        """Get the extracted folder where plot files are located."""
        if not self.extracted_folder or not self.extracted_folder.exists():
            return None
        return self.extracted_folder
