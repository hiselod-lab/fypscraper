"""
PDF Extractor - Layout-preserving PDF extraction to structured JSON.

This package provides tools to extract PDF content with complete layout preservation,
enabling LLM-based processing and PDF regeneration.
"""

from .extractor import PDFExtractor, PDFExtractionError
from .config import VERSION

__version__ = VERSION
__all__ = ["PDFExtractor", "PDFExtractionError", "__version__"]
