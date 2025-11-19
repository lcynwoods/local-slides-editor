"""
Find and replace utilities for post-processing downloaded decks.
Handles URL transformations and path adjustments.
"""
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def replace_in_file(
    file_path: Path,
    replacements: List[Tuple[str, str]],
    use_regex: bool = False
) -> int:
    """
    Perform find/replace operations in a file.
    
    Args:
        file_path: Path to the file
        replacements: List of (find, replace) tuples
        use_regex: Whether to treat patterns as regex
    
    Returns:
        Number of replacements made
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding or skip binary files
        logger.warning(f"Skipping binary file: {file_path}")
        return 0
    
    original_content = content
    total_replacements = 0
    
    for find_str, replace_str in replacements:
        if use_regex:
            content, count = re.subn(find_str, replace_str, content)
        else:
            count = content.count(find_str)
            content = content.replace(find_str, replace_str)
        
        total_replacements += count
        if count > 0:
            logger.debug(f"Replaced '{find_str}' {count} times in {file_path.name}")
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Updated {file_path.name} ({total_replacements} replacements)")
    
    return total_replacements


def replace_in_folder(
    folder: Path,
    replacements: List[Tuple[str, str]],
    file_patterns: List[str] = None,
    use_regex: bool = False
) -> Dict[str, int]:
    """
    Perform find/replace operations across multiple files in a folder.
    
    Args:
        folder: Path to the folder
        replacements: List of (find, replace) tuples
        file_patterns: List of glob patterns to match (default: ['*.html', '*.js', '*.css'])
        use_regex: Whether to treat patterns as regex
    
    Returns:
        Dictionary mapping file paths to replacement counts
    """
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    
    file_patterns = file_patterns or ['*.html', '*.js', '*.css']
    results = {}
    
    for pattern in file_patterns:
        for file_path in folder.rglob(pattern):
            if file_path.is_file():
                count = replace_in_file(file_path, replacements, use_regex)
                if count > 0:
                    results[str(file_path)] = count
    
    total = sum(results.values())
    logger.info(f"Replaced {total} occurrences across {len(results)} files")
    return results


def convert_remote_urls_to_local(
    deck_folder: Path,
    remote_base_url: str,
    local_port: int,
    file_patterns: List[str] = None
) -> Dict[str, int]:
    """
    Convert remote Slides.com URLs back to local server URLs.
    
    This is used after downloading a deck from Slides.com to restore
    references to locally-served plot files.
    
    Args:
        deck_folder: Path to the downloaded deck folder
        remote_base_url: Base URL used by Slides.com for assets
        local_port: Local server port for plot files
        file_patterns: File patterns to search (default: HTML/JS/CSS)
    
    Returns:
        Dictionary of replacement results
    """
    # Create replacement patterns
    replacements = [
        # Replace absolute URLs
        (f'{remote_base_url}/plots/', f'http://localhost:{local_port}/plots/'),
        
        # Replace potential CDN URLs (adjust based on actual Slides.com behavior)
        (r'https://[^/]+/assets/plots/', f'http://localhost:{local_port}/plots/'),
    ]
    
    return replace_in_folder(deck_folder, replacements, file_patterns, use_regex=True)


def convert_local_urls_to_relative(
    deck_folder: Path,
    local_port: int,
    file_patterns: List[str] = None
) -> Dict[str, int]:
    """
    Convert local server URLs to relative paths for offline viewing.
    
    Args:
        deck_folder: Path to the deck folder
        local_port: Local server port
        file_patterns: File patterns to search
    
    Returns:
        Dictionary of replacement results
    """
    replacements = [
        (f'http://localhost:{local_port}/plots/', './plots/'),
    ]
    
    return replace_in_folder(deck_folder, replacements, file_patterns, use_regex=False)


def find_urls_in_file(file_path: Path, pattern: str = None) -> List[str]:
    """
    Find all URLs in a file matching a pattern.
    
    Args:
        file_path: Path to the file
        pattern: Regex pattern to match (default: all HTTP(S) URLs)
    
    Returns:
        List of found URLs
    """
    if not file_path.exists():
        return []
    
    pattern = pattern or r'https?://[^\s<>"]+|localhost:\d+/[^\s<>"]+'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        urls = re.findall(pattern, content)
        return list(set(urls))  # Remove duplicates
    
    except UnicodeDecodeError:
        return []


def preview_replacements(
    file_path: Path,
    replacements: List[Tuple[str, str]],
    context_chars: int = 50
) -> List[Dict[str, str]]:
    """
    Preview replacements without making changes.
    
    Args:
        file_path: Path to the file
        replacements: List of (find, replace) tuples
        context_chars: Number of context characters to show
    
    Returns:
        List of dictionaries with preview information
    """
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        return []
    
    previews = []
    for find_str, replace_str in replacements:
        for match in re.finditer(re.escape(find_str), content):
            start = max(0, match.start() - context_chars)
            end = min(len(content), match.end() + context_chars)
            
            previews.append({
                'find': find_str,
                'replace': replace_str,
                'before': content[start:end],
                'position': match.start()
            })
    
    return previews
