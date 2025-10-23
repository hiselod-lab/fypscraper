"""
Text extraction processor with layout preservation.
"""

from typing import List, Dict
from .font_registry import FontRegistry
from .utils import bbox_dict, parse_color_int
from .config import (
    BLOCK_TYPE_TEXT,
    PYMUPDF_BLOCK_TYPE_TEXT,
    FONT_FLAG_SUPERSCRIPT,
    FONT_FLAG_ITALIC,
    TEXT_DIR_LTR,
    TEXT_DIR_RTL
)


class TextProcessor:
    """
    Processes text extraction from PDF pages with layout preservation.
    """

    def __init__(self, font_registry: FontRegistry):
        """
        Initialize text processor.

        Args:
            font_registry: Global font registry instance
        """
        self.font_registry = font_registry

    def extract_text_blocks(self, page, page_num: int) -> List[dict]:
        """
        Extract all text blocks from a page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            List of text block dictionaries
        """
        text_blocks = []

        # Get page text with layout information
        try:
            text_dict = page.get_text("dict")
        except Exception as e:
            print(f"Warning: Failed to extract text from page {page_num + 1}: {e}")
            return text_blocks

        blocks = text_dict.get("blocks", [])

        block_index = 0
        for block in blocks:
            # Only process text blocks (type 0)
            if block.get("type") != PYMUPDF_BLOCK_TYPE_TEXT:
                continue

            # Extract block-level bounding box
            block_bbox = block.get("bbox", [0, 0, 0, 0])

            # Create block ID
            block_id = f"p{page_num + 1}_b{block_index}"

            # Extract lines from block
            lines = self._extract_lines(block.get("lines", []))

            if not lines:
                # Skip empty blocks
                continue

            # Build text block
            text_block = {
                "block_id": block_id,
                "block_type": BLOCK_TYPE_TEXT,
                "bbox": bbox_dict(*block_bbox),
                "z_index": 0,  # Will be assigned later
                "data": {
                    "type": BLOCK_TYPE_TEXT,
                    "lines": lines
                }
            }

            text_blocks.append(text_block)
            block_index += 1

        return text_blocks

    def _extract_lines(self, lines: List[dict]) -> List[dict]:
        """
        Extract line information with spans.

        Args:
            lines: List of line dictionaries from PyMuPDF

        Returns:
            List of processed line dictionaries
        """
        processed_lines = []

        for line in lines:
            line_bbox = line.get("bbox", [0, 0, 0, 0])

            # Extract text direction (default to ltr)
            direction = line.get("dir", (1, 0))
            text_dir = TEXT_DIR_RTL if direction[0] < 0 else TEXT_DIR_LTR

            # Extract spans
            spans = self._extract_spans(line.get("spans", []))

            if not spans:
                # Skip empty lines
                continue

            processed_line = {
                "bbox": bbox_dict(*line_bbox),
                "spans": spans,
                "direction": text_dir
            }

            processed_lines.append(processed_line)

        return processed_lines

    def _extract_spans(self, spans: List[dict]) -> List[dict]:
        """
        Extract span information with text, font, and styling.

        Args:
            spans: List of span dictionaries from PyMuPDF

        Returns:
            List of processed span dictionaries
        """
        processed_spans = []

        for span in spans:
            # Extract text content
            text = span.get("text", "")

            # Skip empty spans
            if not text:
                continue

            # Extract bounding box
            span_bbox = span.get("bbox", [0, 0, 0, 0])

            # Extract font information
            font_name = span.get("font", "Unknown")
            font_size = span.get("size", 12.0)
            font_flags = span.get("flags", 0)

            # Register font and get font_id
            font_id = self.font_registry.register_font(font_name, font_flags)

            # Extract color
            color_int = span.get("color", 0)
            color = parse_color_int(color_int)

            # Parse font flags for additional styling
            flags = self._parse_font_flags(font_flags)

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

    def _parse_font_flags(self, flags: int) -> dict:
        """
        Parse PyMuPDF font flags bitmask.

        Args:
            flags: Integer bitmask

        Returns:
            Dictionary of boolean flags
        """
        return {
            "superscript": (flags & FONT_FLAG_SUPERSCRIPT) != 0,
            "subscript": False,  # PyMuPDF doesn't provide subscript flag
            "underline": False,  # Not available in flags
            "strikethrough": False  # Not available in flags
        }
