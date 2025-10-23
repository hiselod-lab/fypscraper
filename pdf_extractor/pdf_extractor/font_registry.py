"""
Global font registry for managing fonts across the document.
"""

from typing import Dict
from .utils import generate_font_id, parse_font_family
from .config import (
    FONT_FLAG_BOLD,
    FONT_FLAG_ITALIC,
    FONT_FLAG_MONOSPACED,
    FONT_FLAG_SERIFED
)


class FontRegistry:
    """
    Singleton font registry to manage fonts across entire document.
    """

    def __init__(self):
        """Initialize empty font registry."""
        self.fonts: Dict[str, dict] = {}

    def register_font(self, font_name: str, flags: int) -> str:
        """
        Register a font in the registry.

        Args:
            font_name: Full font name from PyMuPDF
            flags: Font flags bitmask from PyMuPDF

        Returns:
            font_id: Unique font identifier
        """
        # Generate font ID
        font_id = generate_font_id(font_name)

        # If already registered, return existing ID
        if font_id in self.fonts:
            return font_id

        # Parse font properties
        family = parse_font_family(font_name)
        is_bold = (flags & FONT_FLAG_BOLD) != 0
        is_italic = (flags & FONT_FLAG_ITALIC) != 0
        is_monospace = (flags & FONT_FLAG_MONOSPACED) != 0
        is_serif = (flags & FONT_FLAG_SERIFED) != 0

        # Also check font name for bold/italic indicators
        font_name_lower = font_name.lower()
        if 'bold' in font_name_lower:
            is_bold = True
        if 'italic' in font_name_lower or 'oblique' in font_name_lower:
            is_italic = True

        # Register font
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
        """
        Get all registered fonts.

        Returns:
            Dictionary of all fonts
        """
        return self.fonts

    def get_font(self, font_id: str) -> dict:
        """
        Get specific font by ID.

        Args:
            font_id: Font identifier

        Returns:
            Font dictionary or None if not found
        """
        return self.fonts.get(font_id)

    def clear(self):
        """Clear all registered fonts."""
        self.fonts.clear()

    def font_count(self) -> int:
        """
        Get number of registered fonts.

        Returns:
            Count of fonts
        """
        return len(self.fonts)
