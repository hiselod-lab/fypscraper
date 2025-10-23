"""
PDF Extractor - Complete extraction pipeline in a single file.

Extracts PDF content to structured JSON with layout preservation.
Supports: text, images, tables, shapes, OCR, multi-language detection.
"""

import os
import sys
import time
import json
import base64
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional

import pymupdf as fitz  # PyMuPDF
import pdfplumber


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

VERSION = "1.0.0"

# OCR Settings
DEFAULT_OCR_LANGUAGE = "eng"
OCR_CONFIDENCE_THRESHOLD = 60
OCR_PSM_MODE = 3  # Fully automatic page segmentation
OCR_OEM_MODE = 3  # LSTM neural net mode

# Image and OCR Thresholds
LARGE_IMAGE_THRESHOLD = 0.5
MIN_TEXT_FOR_NO_OCR = 50

# JSON Output Settings
JSON_INDENT = 2

# Font Settings
FONT_ID_PREFIX = "f_"
FONT_HASH_LENGTH = 8

# Error Messages
ERROR_INVALID_PDF = "Invalid or corrupted PDF file"
ERROR_ENCRYPTED_PDF = "PDF is password-protected"
ERROR_EMPTY_PDF = "PDF contains no pages"
ERROR_FILE_NOT_FOUND = "PDF file not found"
ERROR_PERMISSION_DENIED = "Permission denied to read PDF file"

# Warning Types
WARNING_MISSING_FONT = "missing_font"
WARNING_CORRUPT_IMAGE = "corrupt_image"
WARNING_TABLE_DETECTION_UNCERTAIN = "table_detection_uncertain"
WARNING_OCR_FAILED = "ocr_failed"
WARNING_SHAPE_EXTRACTION_LIMITED = "shape_extraction_limited"

# Block Types
BLOCK_TYPE_TEXT = "text"
BLOCK_TYPE_IMAGE = "image"
BLOCK_TYPE_TABLE = "table"
BLOCK_TYPE_SHAPE = "shape"

# Shape Types
SHAPE_TYPE_LINE = "line"
SHAPE_TYPE_RECT = "rect"
SHAPE_TYPE_CURVE = "curve"

# Text Direction
TEXT_DIR_LTR = "ltr"
TEXT_DIR_RTL = "rtl"

# Alignment Types
ALIGN_LEFT = "left"
ALIGN_CENTER = "center"
ALIGN_RIGHT = "right"
ALIGN_JUSTIFY = "justify"

# Border Styles
BORDER_STYLE_SOLID = "solid"
BORDER_STYLE_DASHED = "dashed"
BORDER_STYLE_DOTTED = "dotted"

# PyMuPDF Constants
PYMUPDF_BLOCK_TYPE_TEXT = 0
PYMUPDF_BLOCK_TYPE_IMAGE = 1

# Font Flag Bitmasks
FONT_FLAG_SUPERSCRIPT = 1
FONT_FLAG_ITALIC = 2
FONT_FLAG_MONOSPACED = 4
FONT_FLAG_SERIFED = 8
FONT_FLAG_BOLD = 16

# Z-Index Ranges
ZINDEX_SHAPE_START = 1
ZINDEX_IMAGE_START = 1000
ZINDEX_TABLE_START = 2000
ZINDEX_TEXT_START = 3000

# Colorspace Types
COLORSPACE_RGB = "RGB"
COLORSPACE_CMYK = "CMYK"
COLORSPACE_GRAY = "Gray"

# Table Detection Settings
TABLE_MIN_ROWS = 2
TABLE_MIN_COLS = 2


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_pdf(pdf_path: str) -> bool:
    """Validate if file is a readable PDF."""
    if not os.path.exists(pdf_path):
        return False
    if not os.access(pdf_path, os.R_OK):
        return False
    try:
        doc = fitz.open(pdf_path)
        doc.close()
        return True
    except Exception:
        return False


def generate_output_filename(input_path: str, timestamp: bool = False) -> str:
    """Generate output filename from input PDF path."""
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_extracted.json"

    if timestamp or os.path.exists(output_path):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{base}_extracted_{timestamp_str}.json"

    return output_path


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def detect_languages(text: str) -> List[str]:
    """Detect languages in text using character ranges."""
    if not text or len(text.strip()) < 10:
        return []

    languages = set()

    # Check character ranges
    if re.search(r'[a-zA-Z]', text):
        languages.add('en')
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text):
        languages.add('ar')
    if re.search(r'[\u4E00-\u9FFF]', text):
        languages.add('zh')
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        languages.add('ja')
    if re.search(r'[\uAC00-\uD7AF]', text):
        languages.add('ko')
    if re.search(r'[\u0400-\u04FF]', text):
        languages.add('ru')
    if re.search(r'[\u0370-\u03FF]', text):
        languages.add('el')
    if re.search(r'[\u0590-\u05FF]', text):
        languages.add('he')
    if re.search(r'[\u0E00-\u0E7F]', text):
        languages.add('th')
    if re.search(r'[\u0900-\u097F]', text):
        languages.add('hi')

    # Try langdetect if available
    try:
        from langdetect import detect_langs
        detected = detect_langs(text[:1000])
        for lang in detected:
            if lang.prob > 0.5:
                languages.add(lang.lang)
    except Exception:
        pass

    return sorted(list(languages))


def parse_font_family(font_name: str) -> str:
    """Extract font family from full font name."""
    if not font_name:
        return "Unknown"

    name = font_name
    name = re.sub(r'[-,]?(Bold|Italic|Regular|Light|Medium|Heavy|Black|Oblique|MT|PS|MS)+.*$',
                  '', name, flags=re.IGNORECASE)
    name = name.strip('-,_ ')

    return name if name else font_name


def generate_font_id(font_name: str) -> str:
    """Generate unique font ID from font name."""
    hash_obj = hashlib.md5(font_name.encode())
    hash_str = hash_obj.hexdigest()[:FONT_HASH_LENGTH]
    return f"{FONT_ID_PREFIX}{hash_str}"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime as ISO-8601 string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def bbox_dict(x0: float, y0: float, x1: float, y1: float) -> dict:
    """Create bounding box dictionary."""
    return {
        "x0": round(x0, 2),
        "y0": round(y0, 2),
        "x1": round(x1, 2),
        "y1": round(y1, 2)
    }


def color_dict(r: int, g: int, b: int) -> dict:
    """Create color dictionary."""
    return {
        "r": r,
        "g": g,
        "b": b,
        "hex": f"#{r:02x}{g:02x}{b:02x}"
    }


def parse_color_int(color_int: int) -> dict:
    """Parse PyMuPDF color integer to RGB dict."""
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return color_dict(r, g, b)


def calculate_alignment(text_x0: float, text_x1: float, cell_x0: float, cell_x1: float) -> str:
    """Calculate text alignment within a cell."""
    cell_width = cell_x1 - cell_x0
    if cell_width == 0:
        return ALIGN_LEFT

    left_margin = text_x0 - cell_x0
    right_margin = cell_x1 - text_x1
    tolerance = cell_width * 0.05

    if abs(left_margin - right_margin) < tolerance:
        return ALIGN_CENTER
    if left_margin < tolerance:
        return ALIGN_LEFT
    if right_margin < tolerance:
        return ALIGN_RIGHT

    return ALIGN_LEFT


# ============================================================================
# FONT REGISTRY
# ============================================================================

class FontRegistry:
    """Global font registry to manage fonts across entire document."""

    def __init__(self):
        """Initialize empty font registry."""
        self.fonts: Dict[str, dict] = {}

    def register_font(self, font_name: str, flags: int) -> str:
        """Register a font and return its ID."""
        font_id = generate_font_id(font_name)

        if font_id in self.fonts:
            return font_id

        # Parse font properties
        family = parse_font_family(font_name)
        is_bold = (flags & FONT_FLAG_BOLD) != 0
        is_italic = (flags & FONT_FLAG_ITALIC) != 0
        is_monospace = (flags & FONT_FLAG_MONOSPACED) != 0
        is_serif = (flags & FONT_FLAG_SERIFED) != 0

        # Check font name for indicators
        font_name_lower = font_name.lower()
        if 'bold' in font_name_lower:
            is_bold = True
        if 'italic' in font_name_lower or 'oblique' in font_name_lower:
            is_italic = True

        # Register
        self.fonts[font_id] = {
            "name": font_name,
            "family": family,
            "is_bold": is_bold,
            "is_italic": is_italic,
            "is_monospace": is_monospace,
            "is_serif": is_serif
        }

        return font_id

    def get_fonts(self) -> Dict[str, dict]:
        """Get all registered fonts."""
        return self.fonts

    def font_count(self) -> int:
        """Get number of registered fonts."""
        return len(self.fonts)


# ============================================================================
# TEXT PROCESSOR
# ============================================================================

class TextProcessor:
    """Processes text extraction from PDF pages."""

    def __init__(self, font_registry: FontRegistry):
        self.font_registry = font_registry

    def extract_text_blocks(self, page, page_num: int) -> List[dict]:
        """Extract all text blocks from a page."""
        text_blocks = []

        try:
            text_dict = page.get_text("dict")
        except Exception as e:
            print(f"Warning: Failed to extract text from page {page_num + 1}: {e}")
            return text_blocks

        blocks = text_dict.get("blocks", [])
        block_index = 0

        for block in blocks:
            if block.get("type") != PYMUPDF_BLOCK_TYPE_TEXT:
                continue

            block_bbox = block.get("bbox", [0, 0, 0, 0])
            block_id = f"p{page_num + 1}_b{block_index}"

            lines = self._extract_lines(block.get("lines", []))
            if not lines:
                continue

            text_block = {
                "block_id": block_id,
                "block_type": BLOCK_TYPE_TEXT,
                "bbox": bbox_dict(*block_bbox),
                "z_index": 0,
                "data": {
                    "type": BLOCK_TYPE_TEXT,
                    "lines": lines
                }
            }

            text_blocks.append(text_block)
            block_index += 1

        return text_blocks

    def _extract_lines(self, lines: List[dict]) -> List[dict]:
        """Extract line information with spans."""
        processed_lines = []

        for line in lines:
            line_bbox = line.get("bbox", [0, 0, 0, 0])
            direction = line.get("dir", (1, 0))
            text_dir = TEXT_DIR_RTL if direction[0] < 0 else TEXT_DIR_LTR

            spans = self._extract_spans(line.get("spans", []))
            if not spans:
                continue

            processed_line = {
                "bbox": bbox_dict(*line_bbox),
                "spans": spans,
                "direction": text_dir
            }

            processed_lines.append(processed_line)

        return processed_lines

    def _extract_spans(self, spans: List[dict]) -> List[dict]:
        """Extract span information with text, font, and styling."""
        processed_spans = []

        for span in spans:
            text = span.get("text", "")
            if not text:
                continue

            span_bbox = span.get("bbox", [0, 0, 0, 0])
            font_name = span.get("font", "Unknown")
            font_size = span.get("size", 12.0)
            font_flags = span.get("flags", 0)

            font_id = self.font_registry.register_font(font_name, font_flags)
            color_int = span.get("color", 0)
            color = parse_color_int(color_int)

            flags = {
                "superscript": (font_flags & FONT_FLAG_SUPERSCRIPT) != 0,
                "subscript": False,
                "underline": False,
                "strikethrough": False
            }

            processed_span = {
                "text": text,
                "bbox": bbox_dict(*span_bbox),
                "font_id": font_id,
                "font_size": round(font_size, 2),
                "color": color,
                "flags": flags
            }

            processed_spans.append(processed_span)

        return processed_spans


# ============================================================================
# IMAGE PROCESSOR
# ============================================================================

class ImageProcessor:
    """Processes image extraction and OCR from PDF pages."""

    def __init__(self, ocr_enabled: bool = True, ocr_language: str = DEFAULT_OCR_LANGUAGE):
        self.ocr_enabled = ocr_enabled
        self.ocr_language = ocr_language
        self.warnings = []

    def extract_images(self, page, doc, page_num: int, page_text_length: int) -> List[dict]:
        """Extract all images from a page."""
        image_blocks = []

        try:
            image_list = page.get_images(full=True)
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            # Build bbox map
            image_bboxes = {}
            for block in blocks:
                if block.get("type") == PYMUPDF_BLOCK_TYPE_IMAGE:
                    img_bbox = block.get("bbox", [0, 0, 0, 0])
                    image_bboxes[tuple(img_bbox)] = img_bbox

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    image_data = doc.extract_image(xref)
                except Exception as e:
                    self.warnings.append({
                        "page": page_num + 1,
                        "type": WARNING_CORRUPT_IMAGE,
                        "message": f"Failed to extract image {img_index}: {e}"
                    })
                    continue

                image_bytes = image_data.get("image", b"")
                if not image_bytes:
                    continue

                image_format = image_data.get("ext", "png")
                width = image_data.get("width", 0)
                height = image_data.get("height", 0)
                colorspace_int = image_data.get("colorspace", 3)
                colorspace = self._parse_colorspace(colorspace_int)

                base64_data = base64.b64encode(image_bytes).decode('utf-8')

                # Find bbox
                bbox = [0, 0, width, height]
                if image_bboxes:
                    bbox = list(image_bboxes.values())[min(img_index, len(image_bboxes) - 1)]

                # Check OCR
                should_ocr = self._should_perform_ocr(page, page_text_length, bbox, page.rect)
                ocr_text = None
                is_ocr_processed = False

                if should_ocr and self.ocr_enabled:
                    ocr_text = self.perform_ocr(page)
                    is_ocr_processed = True

                block_id = f"p{page_num + 1}_img{img_index}"

                image_block = {
                    "block_id": block_id,
                    "block_type": BLOCK_TYPE_IMAGE,
                    "bbox": bbox_dict(*bbox),
                    "z_index": 0,
                    "data": {
                        "type": BLOCK_TYPE_IMAGE,
                        "image_data": base64_data,
                        "image_format": image_format,
                        "width": width,
                        "height": height,
                        "dpi": None,
                        "colorspace": colorspace,
                        "has_transparency": image_format in ["png", "gif"],
                        "is_ocr_processed": is_ocr_processed,
                        "ocr_text": ocr_text
                    }
                }

                image_blocks.append(image_block)

        except Exception as e:
            self.warnings.append({
                "page": page_num + 1,
                "type": WARNING_CORRUPT_IMAGE,
                "message": f"Image extraction failed: {e}"
            })

        return image_blocks

    def _should_perform_ocr(self, page, text_length: int, image_bbox: list, page_rect) -> bool:
        """Determine if OCR should be performed."""
        if text_length >= MIN_TEXT_FOR_NO_OCR:
            return False

        img_width = image_bbox[2] - image_bbox[0]
        img_height = image_bbox[3] - image_bbox[1]
        img_area = img_width * img_height
        page_area = page_rect.width * page_rect.height

        if page_area > 0:
            area_ratio = img_area / page_area
            if area_ratio > LARGE_IMAGE_THRESHOLD:
                return True

        return False

    def perform_ocr(self, page) -> Optional[str]:
        """Perform OCR on a page."""
        try:
            import pytesseract
            from PIL import Image
            import io

            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            custom_config = f'--psm {OCR_PSM_MODE} --oem 3'
            text = pytesseract.image_to_string(
                image,
                lang=self.ocr_language,
                config=custom_config
            )

            return text.strip() if text else None

        except ImportError:
            self.warnings.append({
                "page": None,
                "type": WARNING_OCR_FAILED,
                "message": "pytesseract or PIL not available for OCR"
            })
            return None
        except Exception as e:
            self.warnings.append({
                "page": None,
                "type": WARNING_OCR_FAILED,
                "message": f"OCR failed: {e}"
            })
            return None

    def _parse_colorspace(self, colorspace_int: int) -> str:
        """Parse colorspace from PyMuPDF integer."""
        colorspace_map = {
            1: COLORSPACE_GRAY,
            3: COLORSPACE_RGB,
            4: COLORSPACE_CMYK
        }
        return colorspace_map.get(colorspace_int, COLORSPACE_RGB)

    def get_warnings(self) -> List[dict]:
        """Get accumulated warnings."""
        return self.warnings


# ============================================================================
# TABLE PROCESSOR
# ============================================================================

class TableProcessor:
    """Processes table detection and extraction from PDF pages."""

    def __init__(self, font_registry: FontRegistry, table_detection_enabled: bool = True):
        self.font_registry = font_registry
        self.table_detection_enabled = table_detection_enabled
        self.warnings = []

    def extract_tables(self, pdf_path: str, page_num: int, pymupdf_page) -> List[dict]:
        """Extract tables from a page using pdfplumber."""
        if not self.table_detection_enabled:
            return []

        table_blocks = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                plumber_page = pdf.pages[page_num]
                tables = plumber_page.find_tables()

                for table_index, table in enumerate(tables):
                    try:
                        table_data = table.extract()
                    except Exception as e:
                        self.warnings.append({
                            "page": page_num + 1,
                            "type": WARNING_TABLE_DETECTION_UNCERTAIN,
                            "message": f"Table {table_index} extraction failed: {e}"
                        })
                        continue

                    if not table_data:
                        continue

                    table_bbox = table.bbox
                    num_rows = len(table_data)
                    num_cols = len(table_data[0]) if table_data else 0

                    if num_rows < TABLE_MIN_ROWS or num_cols < TABLE_MIN_COLS:
                        continue

                    cells = self._extract_cells(table_data, table_bbox, pymupdf_page)
                    block_id = f"p{page_num + 1}_tbl{table_index}"

                    table_block = {
                        "block_id": block_id,
                        "block_type": BLOCK_TYPE_TABLE,
                        "bbox": bbox_dict(*table_bbox),
                        "z_index": 0,
                        "data": {
                            "type": BLOCK_TYPE_TABLE,
                            "rows": num_rows,
                            "columns": num_cols,
                            "cells": cells
                        }
                    }

                    table_blocks.append(table_block)

        except Exception as e:
            self.warnings.append({
                "page": page_num + 1,
                "type": WARNING_TABLE_DETECTION_UNCERTAIN,
                "message": f"Table detection failed: {e}"
            })

        return table_blocks

    def _extract_cells(self, table_data: List[List], table_bbox: tuple, pymupdf_page) -> List[dict]:
        """Extract cell information from table data."""
        cells = []

        if not table_data:
            return cells

        num_rows = len(table_data)
        num_cols = len(table_data[0]) if table_data else 0

        table_x0, table_y0, table_x1, table_y1 = table_bbox
        table_width = table_x1 - table_x0
        table_height = table_y1 - table_y0

        cell_width = table_width / num_cols if num_cols > 0 else 0
        cell_height = table_height / num_rows if num_rows > 0 else 0

        for row_idx, row in enumerate(table_data):
            for col_idx, cell_text in enumerate(row):
                cell_x0 = table_x0 + (col_idx * cell_width)
                cell_y0 = table_y0 + (row_idx * cell_height)
                cell_x1 = cell_x0 + cell_width
                cell_y1 = cell_y0 + cell_height

                content = self._extract_cell_content(
                    cell_text or "",
                    (cell_x0, cell_y0, cell_x1, cell_y1),
                    pymupdf_page
                )

                borders = {
                    "top": {"width": 1.0, "color": color_dict(0, 0, 0), "style": BORDER_STYLE_SOLID},
                    "right": {"width": 1.0, "color": color_dict(0, 0, 0), "style": BORDER_STYLE_SOLID},
                    "bottom": {"width": 1.0, "color": color_dict(0, 0, 0), "style": BORDER_STYLE_SOLID},
                    "left": {"width": 1.0, "color": color_dict(0, 0, 0), "style": BORDER_STYLE_SOLID}
                }

                cell = {
                    "row": row_idx,
                    "column": col_idx,
                    "rowspan": 1,
                    "colspan": 1,
                    "bbox": bbox_dict(cell_x0, cell_y0, cell_x1, cell_y1),
                    "content": content,
                    "borders": borders,
                    "background_color": None
                }

                cells.append(cell)

        return cells

    def _extract_cell_content(self, cell_text: str, cell_bbox: tuple, pymupdf_page) -> List[dict]:
        """Extract formatted content within a cell."""
        if not cell_text:
            return []

        try:
            text_dict = pymupdf_page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            cell_x0, cell_y0, cell_x1, cell_y1 = cell_bbox

            for block in blocks:
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                        span_x0, span_y0, span_x1, span_y1 = span_bbox

                        if (span_x0 >= cell_x0 and span_x1 <= cell_x1 and
                            span_y0 >= cell_y0 and span_y1 <= cell_y1):

                            font_name = span.get("font", "Unknown")
                            font_flags = span.get("flags", 0)
                            font_id = self.font_registry.register_font(font_name, font_flags)
                            font_size = span.get("size", 12.0)
                            color_int = span.get("color", 0)
                            color = parse_color_int(color_int)
                            alignment = calculate_alignment(span_x0, span_x1, cell_x0, cell_x1)

                            return [{
                                "type": "text",
                                "text": cell_text,
                                "font_id": font_id,
                                "font_size": round(font_size, 2),
                                "color": color,
                                "alignment": alignment
                            }]

        except Exception:
            pass

        # Fallback
        return [{
            "type": "text",
            "text": cell_text,
            "font_id": None,
            "font_size": 12.0,
            "color": color_dict(0, 0, 0),
            "alignment": "left"
        }]

    def get_warnings(self) -> List[dict]:
        """Get accumulated warnings."""
        return self.warnings


# ============================================================================
# SHAPE PROCESSOR
# ============================================================================

class ShapeProcessor:
    """Processes shape and line extraction from PDF pages."""

    def __init__(self, shape_extraction_enabled: bool = True):
        self.shape_extraction_enabled = shape_extraction_enabled
        self.warnings = []

    def extract_shapes(self, page, page_num: int) -> List[dict]:
        """Extract shapes and lines from a page."""
        if not self.shape_extraction_enabled:
            return []

        shape_blocks = []

        try:
            if hasattr(page, 'get_drawings'):
                drawings = page.get_drawings()

                for shape_index, drawing in enumerate(drawings):
                    shape_block = self._parse_drawing(drawing, page_num, shape_index)
                    if shape_block:
                        shape_blocks.append(shape_block)
            else:
                self.warnings.append({
                    "page": page_num + 1,
                    "type": WARNING_SHAPE_EXTRACTION_LIMITED,
                    "message": "Shape extraction limited (PyMuPDF version < 1.18)"
                })

        except Exception as e:
            self.warnings.append({
                "page": page_num + 1,
                "type": WARNING_SHAPE_EXTRACTION_LIMITED,
                "message": f"Shape extraction failed: {e}"
            })

        return shape_blocks

    def _parse_drawing(self, drawing: dict, page_num: int, shape_index: int) -> dict:
        """Parse a drawing object into a shape block."""
        try:
            draw_type = drawing.get("type", "")

            shape_type = SHAPE_TYPE_LINE
            if draw_type == "re":
                shape_type = SHAPE_TYPE_RECT
            elif draw_type == "c":
                shape_type = SHAPE_TYPE_CURVE

            rect = drawing.get("rect", [0, 0, 0, 0])

            stroke_color = drawing.get("color", None)
            if stroke_color:
                r = int(stroke_color[0] * 255)
                g = int(stroke_color[1] * 255)
                b = int(stroke_color[2] * 255)
                stroke_color_dict = color_dict(r, g, b)
            else:
                stroke_color_dict = color_dict(0, 0, 0)

            stroke_width = drawing.get("width", 1.0)

            fill_color = drawing.get("fill", None)
            if fill_color:
                r = int(fill_color[0] * 255)
                g = int(fill_color[1] * 255)
                b = int(fill_color[2] * 255)
                fill_color_dict = color_dict(r, g, b)
            else:
                fill_color_dict = None

            items = drawing.get("items", [])
            points = []

            for item in items:
                item_type = item[0]
                if item_type in ["l", "c", "re"]:
                    if len(item) > 1:
                        point = item[1]
                        if isinstance(point, (list, tuple)) and len(point) >= 2:
                            points.append({"x": round(point[0], 2), "y": round(point[1], 2)})

            if not points and shape_type == SHAPE_TYPE_RECT:
                x0, y0, x1, y1 = rect
                points = [
                    {"x": round(x0, 2), "y": round(y0, 2)},
                    {"x": round(x1, 2), "y": round(y0, 2)},
                    {"x": round(x1, 2), "y": round(y1, 2)},
                    {"x": round(x0, 2), "y": round(y1, 2)}
                ]

            block_id = f"p{page_num + 1}_shp{shape_index}"

            shape_block = {
                "block_id": block_id,
                "block_type": BLOCK_TYPE_SHAPE,
                "bbox": bbox_dict(*rect),
                "z_index": 0,
                "data": {
                    "type": BLOCK_TYPE_SHAPE,
                    "shape_type": shape_type,
                    "stroke": {
                        "color": stroke_color_dict,
                        "width": round(stroke_width, 2),
                        "style": BORDER_STYLE_SOLID
                    },
                    "fill": {
                        "color": fill_color_dict
                    },
                    "points": points
                }
            }

            return shape_block

        except Exception as e:
            self.warnings.append({
                "page": page_num + 1,
                "type": WARNING_SHAPE_EXTRACTION_LIMITED,
                "message": f"Failed to parse shape {shape_index}: {e}"
            })
            return None

    def get_warnings(self) -> List[dict]:
        """Get accumulated warnings."""
        return self.warnings


# ============================================================================
# JSON BUILDER
# ============================================================================

class JSONBuilder:
    """Builds and serializes the final JSON structure."""

    @staticmethod
    def build(metadata: dict, pages: List[dict], fonts: dict, extraction_meta: dict) -> dict:
        """Assemble the complete JSON structure."""
        return {
            "document_metadata": metadata,
            "fonts": fonts,
            "pages": pages,
            "extraction_metadata": extraction_meta
        }

    @staticmethod
    def serialize(data: dict, output_path: str, pretty: bool = True) -> None:
        """Write JSON to file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=JSON_INDENT, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to write JSON file: {e}")


# ============================================================================
# MAIN EXTRACTOR
# ============================================================================

class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors."""
    pass


class PDFExtractor:
    """
    Main PDF extraction class that orchestrates the entire extraction process.

    Usage:
        extractor = PDFExtractor("document.pdf")
        data = extractor.extract()

        # Or write directly to file:
        extractor.extract_to_file("output.json")
    """

    def __init__(self, pdf_path: str, options: Optional[Dict] = None):
        """
        Initialize PDF extractor.

        Args:
            pdf_path: Path to PDF file
            options: Optional configuration dict with keys:
                - ocr_enabled: bool (default True)
                - ocr_language: str (default "eng")
                - table_detection_enabled: bool (default True)
                - shape_extraction_enabled: bool (default True)
                - verbose: bool (default False)

        Raises:
            PDFExtractionError: If PDF is invalid or cannot be opened
        """
        self.pdf_path = pdf_path
        self.options = options or {}

        # Extract options
        self.ocr_enabled = self.options.get("ocr_enabled", True)
        self.ocr_language = self.options.get("ocr_language", "eng")
        self.table_detection_enabled = self.options.get("table_detection_enabled", True)
        self.shape_extraction_enabled = self.options.get("shape_extraction_enabled", True)
        self.verbose = self.options.get("verbose", False)

        # Validate PDF
        if not os.path.exists(pdf_path):
            raise PDFExtractionError(ERROR_FILE_NOT_FOUND)

        if not os.access(pdf_path, os.R_OK):
            raise PDFExtractionError(ERROR_PERMISSION_DENIED)

        if not validate_pdf(pdf_path):
            raise PDFExtractionError(ERROR_INVALID_PDF)

        # Initialize components
        self.font_registry = FontRegistry()
        self.text_processor = TextProcessor(self.font_registry)
        self.image_processor = ImageProcessor(self.ocr_enabled, self.ocr_language)
        self.table_processor = TableProcessor(self.font_registry, self.table_detection_enabled)
        self.shape_processor = ShapeProcessor(self.shape_extraction_enabled)

        # Storage
        self.warnings = []
        self.pages = []
        self.doc = None
        self.ocr_pages = []

        # Performance tracking
        self.start_time = None
        self.end_time = None

    def extract(self) -> dict:
        """
        Main extraction method.

        Returns:
            Complete JSON structure as Python dict

        Raises:
            PDFExtractionError: If extraction fails
        """
        self.start_time = time.time()

        try:
            # Phase 1: Document initialization
            self._log("Opening PDF document...")
            metadata = self._extract_metadata()

            # Phase 2: Page-by-page processing
            page_count = self.doc.page_count
            self._log(f"Processing {page_count} pages...")

            for page_num in range(page_count):
                self._log(f"Processing page {page_num + 1}/{page_count}...")
                page_start = time.time()

                page_data = self._process_page(page_num)
                self.pages.append(page_data)

                page_time = time.time() - page_start
                if self.verbose:
                    print(f"  Page {page_num + 1} completed in {page_time:.2f}s")

            # Phase 3: Finalization
            self._log("Finalizing extraction...")
            result = self._finalize(metadata)

            self.end_time = time.time()
            self._log(f"Extraction completed in {self.end_time - self.start_time:.2f}s")

            return result

        except Exception as e:
            if isinstance(e, PDFExtractionError):
                raise
            raise PDFExtractionError(f"Extraction failed: {e}")

        finally:
            if self.doc:
                self.doc.close()

    def extract_to_file(self, output_path: Optional[str] = None) -> str:
        """
        Extract PDF and write JSON to file.

        Args:
            output_path: Output file path (optional, auto-generated if None)

        Returns:
            Output file path

        Raises:
            PDFExtractionError: If extraction fails
            IOError: If file write fails
        """
        data = self.extract()

        if output_path is None:
            output_path = generate_output_filename(self.pdf_path)

        JSONBuilder.serialize(data, output_path, pretty=True)

        return output_path

    def _extract_metadata(self) -> dict:
        """Extract document metadata."""
        try:
            self.doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise PDFExtractionError(f"{ERROR_INVALID_PDF}: {e}")

        if self.doc.is_encrypted:
            raise PDFExtractionError(ERROR_ENCRYPTED_PDF)

        if self.doc.page_count == 0:
            raise PDFExtractionError(ERROR_EMPTY_PDF)

        meta = self.doc.metadata or {}

        metadata = {
            "title": meta.get("title") or None,
            "author": meta.get("author") or None,
            "subject": meta.get("subject") or None,
            "creator": meta.get("creator") or None,
            "producer": meta.get("producer") or None,
            "creation_date": meta.get("creationDate") or None,
            "modification_date": meta.get("modDate") or None,
            "page_count": self.doc.page_count,
            "pdf_version": f"{self.doc.pdf_version[0]}.{self.doc.pdf_version[1]}" if hasattr(self.doc, 'pdf_version') else "1.4",
            "is_encrypted": self.doc.is_encrypted,
            "is_linearized": False
        }

        return metadata

    def _process_page(self, page_num: int) -> dict:
        """Process a single page."""
        page = self.doc.load_page(page_num)

        # Extract dimensions
        rect = page.rect
        dimensions = {
            "width": round(rect.width, 2),
            "height": round(rect.height, 2),
            "rotation": page.rotation
        }

        content_blocks = []

        # Step 1: Extract shapes
        if self.shape_extraction_enabled:
            shapes = self.shape_processor.extract_shapes(page, page_num)
            content_blocks.extend(shapes)
            self.warnings.extend(self.shape_processor.get_warnings())

        # Step 2: Extract text
        text_blocks = self.text_processor.extract_text_blocks(page, page_num)
        content_blocks.extend(text_blocks)
        page_text_length = self._calculate_text_length(text_blocks)

        # Step 3: Extract images
        image_blocks = self.image_processor.extract_images(page, self.doc, page_num, page_text_length)
        content_blocks.extend(image_blocks)
        self.warnings.extend(self.image_processor.get_warnings())

        # Track OCR pages
        for img_block in image_blocks:
            if img_block["data"].get("is_ocr_processed"):
                if page_num not in self.ocr_pages:
                    self.ocr_pages.append(page_num)

        # Step 4: Extract tables
        if self.table_detection_enabled:
            table_blocks = self.table_processor.extract_tables(self.pdf_path, page_num, page)
            content_blocks.extend(table_blocks)
            self.warnings.extend(self.table_processor.get_warnings())

        # Step 5: Assign z-index
        self._assign_z_index(content_blocks)

        page_data = {
            "page_number": page_num + 1,
            "dimensions": dimensions,
            "content_blocks": content_blocks
        }

        return page_data

    def _assign_z_index(self, content_blocks: List[dict]) -> None:
        """Assign z-index to content blocks based on type."""
        shape_counter = ZINDEX_SHAPE_START
        image_counter = ZINDEX_IMAGE_START
        table_counter = ZINDEX_TABLE_START
        text_counter = ZINDEX_TEXT_START

        for block in content_blocks:
            block_type = block["block_type"]

            if block_type == BLOCK_TYPE_SHAPE:
                block["z_index"] = shape_counter
                shape_counter += 1
            elif block_type == BLOCK_TYPE_IMAGE:
                block["z_index"] = image_counter
                image_counter += 1
            elif block_type == BLOCK_TYPE_TABLE:
                block["z_index"] = table_counter
                table_counter += 1
            elif block_type == BLOCK_TYPE_TEXT:
                block["z_index"] = text_counter
                text_counter += 1

    def _calculate_text_length(self, text_blocks: List[dict]) -> int:
        """Calculate total text length in text blocks."""
        total = 0
        for block in text_blocks:
            for line in block.get("data", {}).get("lines", []):
                for span in line.get("spans", []):
                    total += len(span.get("text", ""))
        return total

    def _finalize(self, metadata: dict) -> dict:
        """Build final JSON structure."""
        fonts = self.font_registry.get_fonts()
        all_text = self._collect_all_text()
        languages = detect_languages(all_text)
        stats = self._calculate_statistics()

        extraction_meta = {
            "extractor_version": VERSION,
            "extraction_timestamp": format_timestamp(),
            "source_file": os.path.basename(self.pdf_path),
            "source_file_size": os.path.getsize(self.pdf_path),
            "source_file_hash": calculate_file_hash(self.pdf_path),
            "processing_time": round(time.time() - self.start_time, 2),
            "ocr_pages": [p + 1 for p in self.ocr_pages],
            "warnings": self.warnings,
            "statistics": {
                **stats,
                "languages_detected": languages
            }
        }

        return JSONBuilder.build(metadata, self.pages, fonts, extraction_meta)

    def _collect_all_text(self) -> str:
        """Collect all text from pages for language detection."""
        texts = []
        for page in self.pages:
            for block in page.get("content_blocks", []):
                if block["block_type"] == BLOCK_TYPE_TEXT:
                    for line in block.get("data", {}).get("lines", []):
                        for span in line.get("spans", []):
                            texts.append(span.get("text", ""))
        return " ".join(texts)

    def _calculate_statistics(self) -> dict:
        """Calculate extraction statistics."""
        total_text = 0
        total_images = 0
        total_tables = 0
        total_shapes = 0

        for page in self.pages:
            for block in page.get("content_blocks", []):
                block_type = block["block_type"]
                if block_type == BLOCK_TYPE_TEXT:
                    total_text += 1
                elif block_type == BLOCK_TYPE_IMAGE:
                    total_images += 1
                elif block_type == BLOCK_TYPE_TABLE:
                    total_tables += 1
                elif block_type == BLOCK_TYPE_SHAPE:
                    total_shapes += 1

        return {
            "total_text_blocks": total_text,
            "total_images": total_images,
            "total_tables": total_tables,
            "total_shapes": total_shapes,
            "fonts_used": self.font_registry.font_count()
        }

    def _log(self, message: str) -> None:
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(message)
