"""
Utility functions for PDF Extractor.
"""

import os
import hashlib
import re
from datetime import datetime
from typing import List, Optional
import pymupdf as fitz  # PyMuPDF


def validate_pdf(pdf_path: str) -> bool:
    """
    Validate if file exists and is a readable PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if valid PDF, False otherwise
    """
    # Check if file exists
    if not os.path.exists(pdf_path):
        return False

    # Check if file is readable
    if not os.access(pdf_path, os.R_OK):
        return False

    # Try opening with PyMuPDF to verify it's a valid PDF
    try:
        doc = fitz.open(pdf_path)
        doc.close()
        return True
    except Exception:
        return False


def generate_output_filename(input_path: str, timestamp: bool = False) -> str:
    """
    Generate output filename from input PDF path.

    Args:
        input_path: Path to input PDF
        timestamp: Whether to append timestamp

    Returns:
        Output JSON filename
    """
    # Get base filename without extension
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_extracted.json"

    # If file exists or timestamp requested, add timestamp
    if timestamp or os.path.exists(output_path):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{base}_extracted_{timestamp_str}.json"

    return output_path


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA-256 hash
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def detect_languages(text: str) -> List[str]:
    """
    Detect languages in text using simple heuristics.

    Args:
        text: Text to analyze

    Returns:
        List of ISO 639-1 language codes
    """
    if not text or len(text.strip()) < 10:
        return []

    languages = set()

    # Check for common character ranges
    # Latin characters (English and European languages)
    if re.search(r'[a-zA-Z]', text):
        languages.add('en')

    # Arabic characters
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text):
        languages.add('ar')

    # Chinese characters (CJK Unified Ideographs)
    if re.search(r'[\u4E00-\u9FFF]', text):
        languages.add('zh')

    # Japanese (Hiragana and Katakana)
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        languages.add('ja')

    # Korean (Hangul)
    if re.search(r'[\uAC00-\uD7AF]', text):
        languages.add('ko')

    # Cyrillic (Russian and related languages)
    if re.search(r'[\u0400-\u04FF]', text):
        languages.add('ru')

    # Greek
    if re.search(r'[\u0370-\u03FF]', text):
        languages.add('el')

    # Hebrew
    if re.search(r'[\u0590-\u05FF]', text):
        languages.add('he')

    # Thai
    if re.search(r'[\u0E00-\u0E7F]', text):
        languages.add('th')

    # Devanagari (Hindi and related languages)
    if re.search(r'[\u0900-\u097F]', text):
        languages.add('hi')

    # Try langdetect for more accurate detection if available
    try:
        from langdetect import detect_langs
        detected = detect_langs(text[:1000])  # Use first 1000 chars
        for lang in detected:
            if lang.prob > 0.5:  # Only high confidence
                languages.add(lang.lang)
    except Exception:
        pass  # langdetect not available or failed

    return sorted(list(languages))


def parse_font_family(font_name: str) -> str:
    """
    Extract font family from full font name.

    Args:
        font_name: Full font name (e.g., "Arial-BoldMT")

    Returns:
        Font family name (e.g., "Arial")
    """
    if not font_name:
        return "Unknown"

    # Remove common suffixes
    name = font_name

    # Remove trailing identifiers
    name = re.sub(r'[-,]?(Bold|Italic|Regular|Light|Medium|Heavy|Black|Oblique|MT|PS|MS)+.*$', '', name, flags=re.IGNORECASE)

    # Clean up
    name = name.strip('-,_ ')

    if not name:
        return font_name

    return name


def generate_font_id(font_name: str) -> str:
    """
    Generate unique font ID from font name.

    Args:
        font_name: Font name

    Returns:
        Font ID (format: f_{hash})
    """
    from .config import FONT_ID_PREFIX, FONT_HASH_LENGTH

    hash_obj = hashlib.md5(font_name.encode())
    hash_str = hash_obj.hexdigest()[:FONT_HASH_LENGTH]

    return f"{FONT_ID_PREFIX}{hash_str}"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO-8601 string.

    Args:
        dt: Datetime object (default: now)

    Returns:
        ISO-8601 formatted string
    """
    if dt is None:
        dt = datetime.now()

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def bbox_dict(x0: float, y0: float, x1: float, y1: float) -> dict:
    """
    Create bounding box dictionary.

    Args:
        x0: Left coordinate
        y0: Top coordinate
        x1: Right coordinate
        y1: Bottom coordinate

    Returns:
        Bounding box dict
    """
    return {
        "x0": round(x0, 2),
        "y0": round(y0, 2),
        "x1": round(x1, 2),
        "y1": round(y1, 2)
    }


def color_dict(r: int, g: int, b: int) -> dict:
    """
    Create color dictionary.

    Args:
        r: Red (0-255)
        g: Green (0-255)
        b: Blue (0-255)

    Returns:
        Color dict with r, g, b, hex
    """
    return {
        "r": r,
        "g": g,
        "b": b,
        "hex": f"#{r:02x}{g:02x}{b:02x}"
    }


def parse_color_int(color_int: int) -> dict:
    """
    Parse PyMuPDF color integer to RGB dict.

    Args:
        color_int: Integer representation of RGB color

    Returns:
        Color dict
    """
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF

    return color_dict(r, g, b)


def calculate_alignment(text_x0: float, text_x1: float, cell_x0: float, cell_x1: float) -> str:
    """
    Calculate text alignment within a cell based on positioning.

    Args:
        text_x0: Text left position
        text_x1: Text right position
        cell_x0: Cell left position
        cell_x1: Cell right position

    Returns:
        Alignment string (left, center, right, justify)
    """
    from .config import ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT

    text_width = text_x1 - text_x0
    cell_width = cell_x1 - cell_x0

    if cell_width == 0:
        return ALIGN_LEFT

    # Calculate distances from edges
    left_margin = text_x0 - cell_x0
    right_margin = cell_x1 - text_x1

    # Tolerance for alignment detection (5% of cell width)
    tolerance = cell_width * 0.05

    # Check if centered
    if abs(left_margin - right_margin) < tolerance:
        return ALIGN_CENTER

    # Check if left-aligned
    if left_margin < tolerance:
        return ALIGN_LEFT

    # Check if right-aligned
    if right_margin < tolerance:
        return ALIGN_RIGHT

    # Default to left
    return ALIGN_LEFT
