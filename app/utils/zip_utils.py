"""
ZIP file utilities for packaging and extracting reveal.js decks.
"""
import zipfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_deck_zip(source_folder: Path, output_zip: Path, exclude_patterns: Optional[list[str]] = None) -> Path:
    """
    Create a ZIP file from a reveal.js deck folder.
    
    Args:
        source_folder: Path to the folder containing the deck
        output_zip: Path where the ZIP file should be created
        exclude_patterns: List of patterns to exclude (e.g., ['*.pyc', '__pycache__'])
    
    Returns:
        Path to the created ZIP file
    """
    if not source_folder.exists():
        raise FileNotFoundError(f"Source folder not found: {source_folder}")
    
    exclude_patterns = exclude_patterns or []
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_folder.rglob('*'):
            if file_path.is_file():
                # Check if file matches exclude patterns
                if any(file_path.match(pattern) for pattern in exclude_patterns):
                    continue
                
                # Add file to zip with relative path
                arcname = file_path.relative_to(source_folder)
                zipf.write(file_path, arcname)
                logger.debug(f"Added to ZIP: {arcname}")
    
    logger.info(f"Created ZIP file: {output_zip} (size: {output_zip.stat().st_size} bytes)")
    return output_zip


def extract_deck_zip(zip_path: Path, output_folder: Path) -> Path:
    """
    Extract a ZIP file to a folder.
    
    Args:
        zip_path: Path to the ZIP file
        output_folder: Path where contents should be extracted
    
    Returns:
        Path to the extraction folder
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")
    
    output_folder.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(output_folder)
        logger.info(f"Extracted {len(zipf.namelist())} files to: {output_folder}")
    
    return output_folder


def list_zip_contents(zip_path: Path) -> list[str]:
    """
    List contents of a ZIP file.
    
    Args:
        zip_path: Path to the ZIP file
    
    Returns:
        List of file paths in the ZIP
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP file not found: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        return zipf.namelist()


def validate_deck_structure(folder: Path) -> bool:
    """
    Validate that a folder contains a valid reveal.js deck structure.
    
    Args:
        folder: Path to the folder to validate
    
    Returns:
        True if valid deck structure, False otherwise
    """
    # Check for index.html (required for reveal.js)
    index_html = folder / "index.html"
    if not index_html.exists():
        logger.warning(f"No index.html found in {folder}")
        return False
    
    logger.info(f"Valid reveal.js deck structure found in {folder}")
    return True
