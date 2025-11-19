"""
Detect reveal.js slide files in HTML.
"""
from pathlib import Path
from typing import List, Tuple
import re


def is_reveal_slides(html_path: Path, max_lines: int = 100) -> bool:
    """
    Check if an HTML file is a reveal.js presentation.
    
    Args:
        html_path: Path to HTML file
        max_lines: Maximum number of lines to check
        
    Returns:
        True if the file appears to be reveal.js slides
    """
    try:
        content = html_path.read_text(encoding='utf-8', errors='ignore')
        
        # Check for reveal.js indicators (case-insensitive)
        content_lower = content.lower()
        
        # Common reveal.js markers
        indicators = [
            'reveal.js',
            'class="reveal"',
            'class="slides"',
            'reveal.initialize',
            'new Reveal(',
            '<div class="reveal">',
            'revealslidedeck'
        ]
        
        return any(indicator in content_lower for indicator in indicators)
        
    except (IOError, UnicodeDecodeError):
        return False


def find_html_files(folder: Path) -> Tuple[List[Path], List[Path]]:
    """
    Find all HTML files in a folder and categorize them.
    
    Args:
        folder: Root folder to search
        
    Returns:
        Tuple of (reveal_slides, plot_files)
        - reveal_slides: List of HTML files that are reveal.js presentations
        - plot_files: List of other HTML files (likely plots)
    """
    reveal_slides = []
    plot_files = []
    
    # Find all HTML files recursively
    for html_file in folder.rglob('*.html'):
        if is_reveal_slides(html_file):
            reveal_slides.append(html_file)
        else:
            plot_files.append(html_file)
    
    return reveal_slides, plot_files
