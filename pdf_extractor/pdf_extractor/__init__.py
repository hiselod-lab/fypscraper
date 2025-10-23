"""
PDF Extractor - Extract PDF content to structured JSON.

Simple, powerful PDF extraction with complete layout preservation.
"""

from .extractor import PDFExtractor, PDFExtractionError, VERSION

__version__ = VERSION
__all__ = ["PDFExtractor", "PDFExtractionError", "__version__"]
