"""
Table detection and extraction processor.
"""

import pdfplumber
from typing import List, Dict, Optional
from .font_registry import FontRegistry
from .utils import bbox_dict, parse_color_int, calculate_alignment
from .config import (
    BLOCK_TYPE_TABLE,
    BORDER_STYLE_SOLID,
    WARNING_TABLE_DETECTION_UNCERTAIN,
    TABLE_MIN_ROWS,
    TABLE_MIN_COLS
)


class TableProcessor:
    """
    Processes table detection and extraction from PDF pages.
    """

    def __init__(self, font_registry: FontRegistry, table_detection_enabled: bool = True):
        """
        Initialize table processor.

        Args:
            font_registry: Global font registry instance
            table_detection_enabled: Whether to detect and extract tables
        """
        self.font_registry = font_registry
        self.table_detection_enabled = table_detection_enabled
        self.warnings = []

    def extract_tables(self, pdf_path: str, page_num: int, pymupdf_page) -> List[dict]:
        """
        Extract tables from a page using pdfplumber.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            pymupdf_page: PyMuPDF page object for text extraction

        Returns:
            List of table block dictionaries
        """
        if not self.table_detection_enabled:
            return []

        table_blocks = []

        try:
            # Open page with pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                # pdfplumber uses 0-indexed pages
                plumber_page = pdf.pages[page_num]

                # Find tables
                tables = plumber_page.find_tables()

                for table_index, table in enumerate(tables):
                    # Extract table data
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

                    # Get table bbox
                    table_bbox = table.bbox

                    # Determine rows and columns
                    num_rows = len(table_data)
                    num_cols = len(table_data[0]) if table_data else 0

                    # Skip if too small
                    if num_rows < TABLE_MIN_ROWS or num_cols < TABLE_MIN_COLS:
                        continue

                    # Extract cells
                    cells = self._extract_cells(table_data, table_bbox, pymupdf_page)

                    # Create block ID
                    block_id = f"p{page_num + 1}_tbl{table_index}"

                    # Build table block
                    table_block = {
                        "block_id": block_id,
                        "block_type": BLOCK_TYPE_TABLE,
                        "bbox": bbox_dict(*table_bbox),
                        "z_index": 0,  # Will be assigned later
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
        """
        Extract cell information from table data.

        Args:
            table_data: 2D array of cell text
            table_bbox: Table bounding box
            pymupdf_page: PyMuPDF page for font extraction

        Returns:
            List of cell dictionaries
        """
        cells = []

        if not table_data:
            return cells

        num_rows = len(table_data)
        num_cols = len(table_data[0]) if table_data else 0

        # Calculate cell dimensions
        table_x0, table_y0, table_x1, table_y1 = table_bbox
        table_width = table_x1 - table_x0
        table_height = table_y1 - table_y0

        cell_width = table_width / num_cols if num_cols > 0 else 0
        cell_height = table_height / num_rows if num_rows > 0 else 0

        for row_idx, row in enumerate(table_data):
            for col_idx, cell_text in enumerate(row):
                # Calculate cell bbox
                cell_x0 = table_x0 + (col_idx * cell_width)
                cell_y0 = table_y0 + (row_idx * cell_height)
                cell_x1 = cell_x0 + cell_width
                cell_y1 = cell_y0 + cell_height

                # Extract cell content with formatting
                content = self._extract_cell_content(
                    cell_text or "",
                    (cell_x0, cell_y0, cell_x1, cell_y1),
                    pymupdf_page
                )

                # Detect borders (simplified - all borders as solid for now)
                borders = {
                    "top": {"width": 1.0, "color": {"r": 0, "g": 0, "b": 0, "hex": "#000000"}, "style": BORDER_STYLE_SOLID},
                    "right": {"width": 1.0, "color": {"r": 0, "g": 0, "b": 0, "hex": "#000000"}, "style": BORDER_STYLE_SOLID},
                    "bottom": {"width": 1.0, "color": {"r": 0, "g": 0, "b": 0, "hex": "#000000"}, "style": BORDER_STYLE_SOLID},
                    "left": {"width": 1.0, "color": {"r": 0, "g": 0, "b": 0, "hex": "#000000"}, "style": BORDER_STYLE_SOLID}
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
        """
        Extract formatted content within a cell.

        Args:
            cell_text: Plain text from pdfplumber
            cell_bbox: Cell bounding box
            pymupdf_page: PyMuPDF page for font extraction

        Returns:
            List of content dictionaries
        """
        if not cell_text:
            return []

        # Get text dict from PyMuPDF
        try:
            text_dict = pymupdf_page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            # Find spans that overlap with cell bbox
            cell_x0, cell_y0, cell_x1, cell_y1 = cell_bbox

            for block in blocks:
                if block.get("type") != 0:  # Only text blocks
                    continue

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                        span_x0, span_y0, span_x1, span_y1 = span_bbox

                        # Check if span overlaps with cell
                        if (span_x0 >= cell_x0 and span_x1 <= cell_x1 and
                            span_y0 >= cell_y0 and span_y1 <= cell_y1):

                            # Extract font information
                            font_name = span.get("font", "Unknown")
                            font_flags = span.get("flags", 0)
                            font_id = self.font_registry.register_font(font_name, font_flags)
                            font_size = span.get("size", 12.0)

                            # Extract color
                            color_int = span.get("color", 0)
                            color = parse_color_int(color_int)

                            # Determine alignment
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

        # Fallback: simple text content without formatting
        return [{
            "type": "text",
            "text": cell_text,
            "font_id": None,
            "font_size": 12.0,
            "color": {"r": 0, "g": 0, "b": 0, "hex": "#000000"},
            "alignment": "left"
        }]

    def get_warnings(self) -> List[dict]:
        """Get accumulated warnings."""
        return self.warnings
