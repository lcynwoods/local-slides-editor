"""
Convert reveal.js HTML decks to Slides.com JSON format.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_html_deck(html_path: Path) -> Dict[str, Any]:
    """
    Parse an HTML deck file into Slides.com JSON structure.
    
    Args:
        html_path: Path to the HTML file
        
    Returns:
        Dictionary with deck JSON structure
    """
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")
        
    html_content = html_path.read_text(encoding='utf-8')
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title_tag = soup.find('title')
    title = title_tag.get_text().strip() if title_tag else html_path.stem
    
    # Find all section elements (slides)
    sections = soup.find_all('section')
    
    # Build deck JSON
    deck_json = {
        'title': title,
        'auto-slide-interval': 0,
        'slide-number': False,
        'loop': False,
        'theme-color': 'white',
        'theme-font': 'overpass',
        'transition': 'slide',
        'slides': []
    }
    
    logger.info(f"Found {len(sections)} sections in HTML")
    
    # Parse slides, handling vertical stacks
    # Find top-level sections (direct children of .slides div)
    slides_div = soup.find('div', class_='slides')
    if slides_div:
        top_sections = slides_div.find_all('section', recursive=False)
    else:
        top_sections = sections
    
    for section in top_sections:
        # Check if this is a vertical stack - two formats:
        # 1. Slides.com export: <section class="stack">
        # 2. Pipeline output: <section> wrapping other <section> elements without data-id
        has_class_stack = 'stack' in section.get('class', [])
        has_data_id = section.get('data-id') is not None
        nested_sections = section.find_all('section', recursive=False)
        
        # It's a vertical stack if:
        # - Has class="stack", OR
        # - Has nested sections AND no data-id (pipeline format)
        is_vertical_stack = has_class_stack or (nested_sections and not has_data_id)
        
        if is_vertical_stack and nested_sections:
            # Parse nested sections as a vertical group
            vertical_group = []
            for nested in nested_sections:
                slide = _parse_slide(nested)
                if slide:
                    vertical_group.append(slide)
            if vertical_group:
                deck_json['slides'].append(vertical_group)
        else:
            slide = _parse_slide(section)
            if slide:
                deck_json['slides'].append(slide)
    
    logger.info(f"Parsed {len(deck_json['slides'])} slides from {html_path.name}")
    return deck_json


def _parse_slide(section) -> Optional[Dict[str, Any]]:
    """Parse a single slide section."""
    slide = {}
    
    # Get slide ID
    slide_id = section.get('data-id')
    if slide_id:
        slide['id'] = slide_id
    
    # Get background properties
    bg_color = section.get('data-background-color')
    if bg_color:
        slide['background-color'] = bg_color
    
    bg_image = section.get('data-background-image')
    if bg_image:
        slide['background-image'] = bg_image
    
    # Get speaker notes
    notes = section.get('data-notes')
    if notes:
        slide['notes'] = notes
    
    # Find all sl-block elements
    blocks = section.find_all('div', class_='sl-block')
    
    if blocks:
        slide['blocks'] = []
        for block_div in blocks:
            block = _parse_block(block_div)
            if block:
                slide['blocks'].append(block)
    
    # If no blocks found, try to extract simple HTML or text
    if not slide.get('blocks'):
        # Get all text content
        text_content = section.get_text(strip=True)
        if text_content:
            slide['html'] = str(section)
    
    return slide if slide else None


def _parse_block(block_div) -> Optional[Dict[str, Any]]:
    """Parse a single content block."""
    block = {}
    
    # Get block type
    block_type = block_div.get('data-block-type', 'text')
    block['type'] = block_type
    
    # Parse positioning from style attribute
    style = block_div.get('style', '')
    position = _parse_style(style)
    block.update(position)
    
    # Find the content div
    content_div = block_div.find('div', class_='sl-block-content')
    if not content_div:
        return None
    
    # Parse content div styling (z-index, background, alignment, etc.)
    content_style = content_div.get('style', '')
    content_styling = _parse_content_style(content_style)
    block.update(content_styling)
    
    # Parse based on block type
    if block_type == 'text':
        # Find heading or paragraph tags
        elem = None
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            elem = content_div.find(tag)
            if elem:
                block['format'] = tag
                break
        
        # If no specific tag found, use content div directly
        if not elem:
            elem = content_div
            block['format'] = 'p'
        
        # Extract clean text (without HTML tags)
        text = elem.get_text(strip=True)
        if text:
            block['value'] = text
            
            # Extract color from inline styles (spans, p/h tags, content div)
            elem_style = elem.get('style', '') if hasattr(elem, 'get') else ''
            color = _extract_text_color(elem, content_style, elem_style)
            if color:
                block['color'] = color
            
            # Extract font-size from inline styles
            font_size = _extract_font_size(elem, content_style, elem_style)
            if font_size:
                block['font-size'] = font_size
            
            # Extract alignment from p/h tag style or content div
            align = _extract_alignment(elem_style, content_style)
            if align:
                block['align'] = align
    
    elif block_type == 'image':
        img = content_div.find('img')
        if img:
            # Try data-src first (lazy loading), then src
            block['value'] = img.get('data-src') or img.get('src', '')
            
            # Capture cropping data if present
            crop_attrs = ['data-crop-x', 'data-crop-y', 'data-crop-width', 'data-crop-height']
            for attr in crop_attrs:
                val = img.get(attr)
                if val:
                    # Convert to JSON-friendly key (remove data- prefix)
                    block[attr.replace('data-', '')] = float(val)
            
            # Capture natural dimensions
            natural_width = img.get('data-natural-width')
            natural_height = img.get('data-natural-height')
            if natural_width:
                block['natural-width'] = int(natural_width)
            if natural_height:
                block['natural-height'] = int(natural_height)
    
    elif block_type == 'iframe':
        iframe = content_div.find('iframe')
        if iframe:
            block['value'] = iframe.get('data-src') or iframe.get('src', '')
    
    elif block_type == 'shape':
        # Shapes are complex, just note their existence
        block['type'] = 'html'
        block['value'] = f'<div class="shape">{content_div.get_text(strip=True)}</div>'
    
    elif block_type == 'line':
        # Lines are SVG, skip for now
        return None
    
    # Only return block if it has content
    return block if block.get('value') else None


def _parse_style(style: str) -> Dict[str, Any]:
    """Extract positioning from inline styles."""
    result = {}
    
    patterns = {
        'width': r'width:\s*(\d+(?:\.\d+)?)px',
        'height': r'height:\s*(\d+(?:\.\d+)?)px',
        'x': r'left:\s*(\d+(?:\.\d+)?)px',
        'y': r'top:\s*(\d+(?:\.\d+)?)px'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, style)
        if match:
            result[key] = int(float(match.group(1)))
            
    return result


def _parse_content_style(style: str) -> Dict[str, Any]:
    """Extract styling properties from content div styles."""
    result = {}
    
    # Z-index for layering
    z_match = re.search(r'z-index:\s*(\d+)', style)
    if z_match:
        result['z-index'] = int(z_match.group(1))
    
    # Background color (of the block, not text)
    bg_match = re.search(r'background-color:\s*([^;]+)', style)
    if bg_match:
        result['background-color'] = bg_match.group(1).strip()
    
    # Text alignment
    align_match = re.search(r'text-align:\s*(\w+)', style)
    if align_match:
        result['text-align'] = align_match.group(1)
    
    # Line height
    line_match = re.search(r'line-height:\s*([^;]+)', style)
    if line_match:
        result['line-height'] = line_match.group(1).strip()
    
    return result


def _extract_text_color(elem, content_style: str, elem_style: str = '') -> Optional[str]:
    """Extract text color from element or content div style."""
    # First check element's own style (p or h tag)
    color_match = re.search(r'color:\s*([^;]+)', elem_style)
    if color_match:
        color = color_match.group(1).strip()
        return _normalize_color(color)
    
    # Then check content div style
    color_match = re.search(r'color:\s*([^;]+)', content_style)
    if color_match:
        color = color_match.group(1).strip()
        return _normalize_color(color)
    
    # Finally check inline styles in spans within the element
    spans = elem.find_all('span') if hasattr(elem, 'find_all') else []
    for span in spans:
        style = span.get('style', '')
        color_match = re.search(r'color:\s*([^;]+)', style)
        if color_match:
            color = color_match.group(1).strip()
            return _normalize_color(color)
    
    return None


def _extract_font_size(elem, content_style: str, elem_style: str = '') -> Optional[str]:
    """Extract font size from inline styles, converting to percentage."""
    # Check element's own style first
    font_match = re.search(r'font-size:\s*([^;]+)', elem_style)
    if font_match:
        size = font_match.group(1).strip()
        return _normalize_font_size(size)
    
    # Check inline styles in spans
    spans = elem.find_all('span') if hasattr(elem, 'find_all') else []
    for span in spans:
        style = span.get('style', '')
        font_match = re.search(r'font-size:\s*([^;]+)', style)
        if font_match:
            size = font_match.group(1).strip()
            # Convert from em or px to percentage if needed
            return _normalize_font_size(size)
    
    # Check content div style
    font_match = re.search(r'font-size:\s*([^;]+)', content_style)
    if font_match:
        size = font_match.group(1).strip()
        return _normalize_font_size(size)
    
    return None


def _extract_alignment(elem_style: str, content_style: str) -> Optional[str]:
    """Extract text alignment from element or content div style."""
    # Check element's own style first (p or h tag)
    align_match = re.search(r'text-align:\s*(\w+)', elem_style)
    if align_match:
        return align_match.group(1)
    
    # Then check content div style
    align_match = re.search(r'text-align:\s*(\w+)', content_style)
    if align_match:
        return align_match.group(1)
    
    return None


def _normalize_color(color: str) -> str:
    """Normalize color format for Slides.com API."""
    color = color.strip()
    
    # Convert rgb(255, 255, 255) to #ffffff
    rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
    if rgb_match:
        r, g, b = map(int, rgb_match.groups())
        return f'#{r:02x}{g:02x}{b:02x}'
    
    # Convert rgba to rgb (ignore alpha)
    rgba_match = re.match(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)', color)
    if rgba_match:
        r, g, b = map(int, rgba_match.groups())
        return f'#{r:02x}{g:02x}{b:02x}'
    
    # Return as-is if already hex or named color
    return color


def _normalize_font_size(size: str) -> str:
    """Normalize font size to percentage for Slides.com API."""
    size = size.strip()
    
    # If already a percentage, return as-is
    if '%' in size:
        return size
    
    # Convert em to percentage (1em = 100%)
    if 'em' in size:
        em_val = float(size.replace('em', ''))
        return f'{int(em_val * 100)}%'
    
    # Convert px to percentage (assuming base of ~16px = 100%)
    # This is approximate - Slides.com uses relative sizing
    if 'px' in size:
        px_val = float(size.replace('px', ''))
        # Base size is roughly 28px for default text
        percentage = int((px_val / 28) * 100)
        return f'{percentage}%'
    
    # Return as-is if we can't convert
    return size


def convert_html_to_json(html_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Convert HTML deck to Slides.com JSON format and save to file.
    
    Args:
        html_path: Path to input HTML file
        output_path: Optional path for output JSON file (defaults to same dir)
        
    Returns:
        Path to the created JSON file
    """
    import json
    
    deck_json = parse_html_deck(html_path)
    
    if output_path is None:
        output_path = html_path.with_suffix('.json')
        
    output_path.write_text(
        json.dumps(deck_json, indent=2),
        encoding='utf-8'
    )
    
    logger.info(f"Saved deck JSON to {output_path}")
    return output_path


def update_plot_urls_in_json(deck_json: Dict[str, Any], url_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Update plot URLs in deck JSON (e.g., convert local paths to hosted URLs).
    
    Args:
        deck_json: Deck JSON structure
        url_mapping: Dictionary mapping old paths to new URLs
        
    Returns:
        Updated deck JSON
    """
    for slide in deck_json.get('slides', []):
        if isinstance(slide, list):
            # Handle vertical slides
            for sub_slide in slide:
                _update_slide_urls(sub_slide, url_mapping)
        else:
            _update_slide_urls(slide, url_mapping)
            
    return deck_json


def _update_slide_urls(slide: Dict[str, Any], url_mapping: Dict[str, str]) -> None:
    """Update URLs in a single slide."""
    for block in slide.get('blocks', []):
        if block.get('type') in ['iframe', 'image'] and 'value' in block:
            old_url = block['value']
            for old_path, new_url in url_mapping.items():
                if old_path in old_url:
                    block['value'] = old_url.replace(old_path, new_url)
                    logger.debug(f"Updated URL: {old_url} -> {block['value']}")
                    break
