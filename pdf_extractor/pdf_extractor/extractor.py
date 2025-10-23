"""
Main PDF extraction orchestrator.
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Optional
import pymupdf as fitz  # PyMuPDF

from .font_registry import FontRegistry
from .text_processor import TextProcessor
from .image_processor import ImageProcessor
from .table_processor import TableProcessor
from .shape_processor import ShapeProcessor
from .json_builder import JSONBuilder
from .utils import (
    validate_pdf,
    generate_output_filename,
    calculate_file_hash,
    detect_languages,
    format_timestamp
)
from .config import (
    VERSION,
    ERROR_INVALID_PDF,
    ERROR_ENCRYPTED_PDF,
    ERROR_EMPTY_PDF,
    ERROR_FILE_NOT_FOUND,
    ERROR_PERMISSION_DENIED,
    BLOCK_TYPE_TEXT,
    BLOCK_TYPE_IMAGE,
    BLOCK_TYPE_TABLE,
    BLOCK_TYPE_SHAPE,
    ZINDEX_SHAPE_START,
    ZINDEX_IMAGE_START,
    ZINDEX_TABLE_START,
    ZINDEX_TEXT_START
)


class PDFExtractionError(Exception):
    """Custom exception for PDF extraction errors."""
    pass


class PDFExtractor:
    """
    Main PDF extraction class that orchestrates the entire extraction process.
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
        self.performance_breakdown = {}

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
        # Extract
        data = self.extract()

        # Generate output path if not provided
        if output_path is None:
            output_path = generate_output_filename(self.pdf_path)

        # Write to file
        JSONBuilder.serialize(data, output_path, pretty=True)

        return output_path

    def _extract_metadata(self) -> dict:
        """
        Extract document metadata.

        Returns:
            Metadata dictionary

        Raises:
            PDFExtractionError: If document cannot be opened
        """
        try:
            self.doc = fitz.open(self.pdf_path)
        except Exception as e:
            raise PDFExtractionError(f"{ERROR_INVALID_PDF}: {e}")

        # Check if encrypted
        if self.doc.is_encrypted:
            raise PDFExtractionError(ERROR_ENCRYPTED_PDF)

        # Check if empty
        if self.doc.page_count == 0:
            raise PDFExtractionError(ERROR_EMPTY_PDF)

        # Extract metadata
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
            "is_linearized": False  # PyMuPDF doesn't easily expose this
        }

        return metadata

    def _process_page(self, page_num: int) -> dict:
        """
        Process a single page.

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Page dictionary
        """
        page = self.doc.load_page(page_num)

        # Extract page dimensions
        rect = page.rect
        dimensions = {
            "width": round(rect.width, 2),
            "height": round(rect.height, 2),
            "rotation": page.rotation
        }

        # Initialize content blocks list
        content_blocks = []

        # Step 1: Extract shapes (lowest z-index)
        if self.shape_extraction_enabled:
            shapes = self.shape_processor.extract_shapes(page, page_num)
            content_blocks.extend(shapes)
            self.warnings.extend(self.shape_processor.get_warnings())

        # Step 2: Extract text blocks
        text_blocks = self.text_processor.extract_text_blocks(page, page_num)
        content_blocks.extend(text_blocks)

        # Calculate text length for OCR decision
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

        # Step 6: Assemble page object
        page_data = {
            "page_number": page_num + 1,  # 1-indexed for user-facing
            "dimensions": dimensions,
            "content_blocks": content_blocks
        }

        # Release page resources
        page = None

        return page_data

    def _assign_z_index(self, content_blocks: List[dict]) -> None:
        """
        Assign z-index to content blocks based on type.

        Args:
            content_blocks: List of content block dictionaries (modified in-place)
        """
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
        """
        Calculate total text length in text blocks.

        Args:
            text_blocks: List of text block dictionaries

        Returns:
            Total character count
        """
        total = 0
        for block in text_blocks:
            for line in block.get("data", {}).get("lines", []):
                for span in line.get("spans", []):
                    total += len(span.get("text", ""))
        return total

    def _finalize(self, metadata: dict) -> dict:
        """
        Build final JSON structure.

        Args:
            metadata: Document metadata

        Returns:
            Complete document dictionary
        """
        # Get fonts
        fonts = self.font_registry.get_fonts()

        # Collect all text for language detection
        all_text = self._collect_all_text()
        languages = detect_languages(all_text)

        # Calculate statistics
        stats = self._calculate_statistics()

        # Build extraction metadata
        extraction_meta = {
            "extractor_version": VERSION,
            "extraction_timestamp": format_timestamp(),
            "source_file": os.path.basename(self.pdf_path),
            "source_file_size": os.path.getsize(self.pdf_path),
            "source_file_hash": calculate_file_hash(self.pdf_path),
            "processing_time": round(time.time() - self.start_time, 2),
            "ocr_pages": [p + 1 for p in self.ocr_pages],  # Convert to 1-indexed
            "warnings": self.warnings,
            "statistics": {
                **stats,
                "languages_detected": languages
            }
        }

        # Assemble final JSON
        return JSONBuilder.build(metadata, self.pages, fonts, extraction_meta)

    def _collect_all_text(self) -> str:
        """
        Collect all text from pages for language detection.

        Returns:
            Concatenated text
        """
        texts = []
        for page in self.pages:
            for block in page.get("content_blocks", []):
                if block["block_type"] == BLOCK_TYPE_TEXT:
                    for line in block.get("data", {}).get("lines", []):
                        for span in line.get("spans", []):
                            texts.append(span.get("text", ""))
        return " ".join(texts)

    def _calculate_statistics(self) -> dict:
        """
        Calculate extraction statistics.

        Returns:
            Statistics dictionary
        """
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
