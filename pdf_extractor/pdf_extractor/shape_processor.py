"""
Shape and line extraction processor.
"""

from typing import List, Dict
from .utils import bbox_dict, color_dict
from .config import (
    BLOCK_TYPE_SHAPE,
    SHAPE_TYPE_LINE,
    SHAPE_TYPE_RECT,
    SHAPE_TYPE_CURVE,
    BORDER_STYLE_SOLID,
    WARNING_SHAPE_EXTRACTION_LIMITED
)


class ShapeProcessor:
    """
    Processes shape and line extraction from PDF pages.
    """

    def __init__(self, shape_extraction_enabled: bool = True):
        """
        Initialize shape processor.

        Args:
            shape_extraction_enabled: Whether to extract shapes
        """
        self.shape_extraction_enabled = shape_extraction_enabled
        self.warnings = []

    def extract_shapes(self, page, page_num: int) -> List[dict]:
        """
        Extract shapes and lines from a page.

        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)

        Returns:
            List of shape block dictionaries
        """
        if not self.shape_extraction_enabled:
            return []

        shape_blocks = []

        try:
            # Try to get drawings (PyMuPDF 1.18+)
            if hasattr(page, 'get_drawings'):
                drawings = page.get_drawings()

                for shape_index, drawing in enumerate(drawings):
                    shape_block = self._parse_drawing(drawing, page_num, shape_index)
                    if shape_block:
                        shape_blocks.append(shape_block)
            else:
                # Fallback for older PyMuPDF versions
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
        """
        Parse a drawing object into a shape block.

        Args:
            drawing: Drawing dictionary from PyMuPDF
            page_num: Page number (0-indexed)
            shape_index: Shape index

        Returns:
            Shape block dictionary or None
        """
        try:
            # Get drawing type
            draw_type = drawing.get("type", "")

            # Map PyMuPDF types to our shape types
            shape_type = SHAPE_TYPE_LINE
            if draw_type == "re":
                shape_type = SHAPE_TYPE_RECT
            elif draw_type == "c":
                shape_type = SHAPE_TYPE_CURVE
            elif draw_type in ["l", "qu"]:
                shape_type = SHAPE_TYPE_LINE

            # Get bounding box
            rect = drawing.get("rect", [0, 0, 0, 0])

            # Get stroke color
            stroke_color = drawing.get("color", None)
            if stroke_color:
                # PyMuPDF returns color as tuple (r, g, b) in 0-1 range
                r = int(stroke_color[0] * 255)
                g = int(stroke_color[1] * 255)
                b = int(stroke_color[2] * 255)
                stroke_color_dict = color_dict(r, g, b)
            else:
                stroke_color_dict = color_dict(0, 0, 0)

            # Get stroke width
            stroke_width = drawing.get("width", 1.0)

            # Get fill color
            fill_color = drawing.get("fill", None)
            if fill_color:
                r = int(fill_color[0] * 255)
                g = int(fill_color[1] * 255)
                b = int(fill_color[2] * 255)
                fill_color_dict = color_dict(r, g, b)
            else:
                fill_color_dict = None

            # Get points
            items = drawing.get("items", [])
            points = []

            for item in items:
                item_type = item[0]
                if item_type in ["l", "c", "re"]:
                    # Line, curve, rectangle
                    if len(item) > 1:
                        point = item[1]
                        if isinstance(point, (list, tuple)) and len(point) >= 2:
                            points.append({"x": round(point[0], 2), "y": round(point[1], 2)})

            # If no points extracted from items, use rect corners
            if not points and shape_type == SHAPE_TYPE_RECT:
                x0, y0, x1, y1 = rect
                points = [
                    {"x": round(x0, 2), "y": round(y0, 2)},
                    {"x": round(x1, 2), "y": round(y0, 2)},
                    {"x": round(x1, 2), "y": round(y1, 2)},
                    {"x": round(x0, 2), "y": round(y1, 2)}
                ]

            # Create block ID
            block_id = f"p{page_num + 1}_shp{shape_index}"

            # Build shape block
            shape_block = {
                "block_id": block_id,
                "block_type": BLOCK_TYPE_SHAPE,
                "bbox": bbox_dict(*rect),
                "z_index": 0,  # Will be assigned later
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
