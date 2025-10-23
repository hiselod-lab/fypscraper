"""
Configuration constants for PDF Extractor.
"""

# Version
VERSION = "1.0.0"

# OCR Settings
DEFAULT_OCR_LANGUAGE = "eng"
OCR_CONFIDENCE_THRESHOLD = 60  # Minimum confidence for OCR text
OCR_PSM_MODE = 3  # Fully automatic page segmentation
OCR_OEM_MODE = 3  # LSTM neural net mode

# Image and OCR Thresholds
LARGE_IMAGE_THRESHOLD = 0.5  # Fraction of page area to consider image "large"
MIN_TEXT_FOR_NO_OCR = 50  # Minimum characters to skip OCR

# Supported Formats
SUPPORTED_IMAGE_FORMATS = ["jpeg", "png", "gif", "bmp", "tiff"]

# JSON Output Settings
JSON_INDENT = 2

# Feature Flags (defaults)
TABLE_DETECTION_ENABLED = True
SHAPE_EXTRACTION_ENABLED = True
OCR_ENABLED = True

# Performance Settings
PAGE_PROCESSING_TIMEOUT = 300  # seconds per page (5 minutes)
MAX_MEMORY_MB = 2048  # Maximum memory usage in MB

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

# PyMuPDF Block Type Constants
PYMUPDF_BLOCK_TYPE_TEXT = 0
PYMUPDF_BLOCK_TYPE_IMAGE = 1

# Font Flag Bitmasks (PyMuPDF)
FONT_FLAG_SUPERSCRIPT = 1
FONT_FLAG_ITALIC = 2
FONT_FLAG_SERIFED = 8
FONT_FLAG_MONOSPACED = 4
FONT_FLAG_BOLD = 16

# Z-Index Ranges (for rendering order)
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
TABLE_SNAP_TOLERANCE = 3  # pixels

# Performance Logging
VERBOSE_LOGGING = False
LOG_PERFORMANCE_BREAKDOWN = True
