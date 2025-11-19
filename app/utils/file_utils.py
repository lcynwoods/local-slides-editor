"""
File utilities for managing deck files and folders.
"""
from pathlib import Path
from typing import Optional, List
import shutil
import logging

logger = logging.getLogger(__name__)


def get_html_files(folder: Path, recursive: bool = True) -> List[Path]:
    """
    Get all HTML files in a folder.
    
    Args:
        folder: Path to search
        recursive: Whether to search recursively
    
    Returns:
        List of HTML file paths
    """
    if not folder.exists():
        return []
    
    pattern = '**/*.html' if recursive else '*.html'
    return sorted(folder.glob(pattern))


def get_plot_files(plots_folder: Path) -> List[Path]:
    """
    Get all Plotly HTML files from the plots folder.
    
    Args:
        plots_folder: Path to the plots folder
    
    Returns:
        List of plot HTML file paths
    """
    if not plots_folder.exists():
        logger.warning(f"Plots folder not found: {plots_folder}")
        return []
    
    plot_files = list(plots_folder.rglob('*.html'))
    logger.info(f"Found {len(plot_files)} plot files in {plots_folder}")
    return sorted(plot_files)


def copy_file(src: Path, dest: Path, overwrite: bool = False) -> Path:
    """
    Copy a file from source to destination.
    
    Args:
        src: Source file path
        dest: Destination file path
        overwrite: Whether to overwrite if destination exists
    
    Returns:
        Path to the copied file
    """
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")
    
    if dest.exists() and not overwrite:
        raise FileExistsError(f"Destination file already exists: {dest}")
    
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    logger.info(f"Copied: {src} -> {dest}")
    return dest


def copy_folder(src: Path, dest: Path, overwrite: bool = False) -> Path:
    """
    Copy an entire folder from source to destination.
    
    Args:
        src: Source folder path
        dest: Destination folder path
        overwrite: Whether to overwrite if destination exists
    
    Returns:
        Path to the copied folder
    """
    if not src.exists():
        raise FileNotFoundError(f"Source folder not found: {src}")
    
    if dest.exists():
        if overwrite:
            shutil.rmtree(dest)
        else:
            raise FileExistsError(f"Destination folder already exists: {dest}")
    
    shutil.copytree(src, dest)
    logger.info(f"Copied folder: {src} -> {dest}")
    return dest


def ensure_folder_exists(folder: Path) -> Path:
    """
    Ensure a folder exists, creating it if necessary.
    
    Args:
        folder: Path to the folder
    
    Returns:
        Path to the folder
    """
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_folder_size(folder: Path) -> int:
    """
    Calculate total size of all files in a folder.
    
    Args:
        folder: Path to the folder
    
    Returns:
        Total size in bytes
    """
    if not folder.exists():
        return 0
    
    total_size = 0
    for file_path in folder.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    
    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def clean_temp_files(folder: Path, patterns: Optional[List[str]] = None) -> int:
    """
    Remove temporary files from a folder.
    
    Args:
        folder: Path to the folder
        patterns: List of glob patterns to match (default: common temp files)
    
    Returns:
        Number of files removed
    """
    if not folder.exists():
        return 0
    
    patterns = patterns or ['*.tmp', '*.temp', '__pycache__', '.DS_Store', 'Thumbs.db']
    removed_count = 0
    
    for pattern in patterns:
        for file_path in folder.rglob(pattern):
            try:
                if file_path.is_file():
                    file_path.unlink()
                    removed_count += 1
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} temporary files from {folder}")
    
    return removed_count
