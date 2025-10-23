"""
Image extraction and OCR processor.
"""

import base64
from typing import List, Dict, Optional
from .utils import bbox_dict
from .config import (
    BLOCK_TYPE_IMAGE,
    PYMUPDF_BLOCK_TYPE_IMAGE,
    MIN_TEXT_FOR_NO_OCR,
    LARGE_IMAGE_THRESHOLD,
    DEFAULT_OCR_LANGUAGE,
    OCR_PSM_MODE,
    COLORSPACE_RGB,
    COLORSPACE_CMYK,
    COLORSPACE_GRAY,
    WARNING_CORRUPT_IMAGE,
    WARNING_OCR_FAILED
)


class ImageProcessor:
    """
    Processes image extraction and OCR from PDF pages.
    """

    def __init__(self, ocr_enabled: bool = True, ocr_language: str = DEFAULT_OCR_LANGUAGE):
        """
        Initialize image processor.

        Args:
            ocr_enabled: Whether to perform OCR on scanned pages
            ocr_language: Language(s) for OCR (e.g., "eng", "eng+ara")
        """
        self.ocr_enabled = ocr_enabled
        self.ocr_language = ocr_language
        self.warnings = []

    def extract_images(self, page, doc, page_num: int, page_text_length: int) -> List[dict]:
        """
        Extract all images from a page.

        Args:
            page: PyMuPDF page object
            doc: PyMuPDF document object
            page_num: Page number (0-indexed)
            page_text_length: Length of extractable text on page

        Returns:
            List of image block dictionaries
        """
        image_blocks = []

        try:
            # Get image list
            image_list = page.get_images(full=True)

            # Get text dict to find image bboxes
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            # Build bbox map for images
            image_bboxes = {}
            for block in blocks:
                if block.get("type") == PYMUPDF_BLOCK_TYPE_IMAGE:
                    # Store bbox by image index
                    img_bbox = block.get("bbox", [0, 0, 0, 0])
                    # PyMuPDF image blocks don't have xref, use bbox to match
                    image_bboxes[tuple(img_bbox)] = img_bbox

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                # Extract image data
                try:
                    image_data = doc.extract_image(xref)
                except Exception as e:
                    self.warnings.append({
                        "page": page_num + 1,
                        "type": WARNING_CORRUPT_IMAGE,
                        "message": f"Failed to extract image {img_index}: {e}"
                    })
                    continue

                # Get image bytes
                image_bytes = image_data.get("image", b"")
                if not image_bytes:
                    continue

                # Get image format
                image_format = image_data.get("ext", "png")

                # Get image dimensions
                width = image_data.get("width", 0)
                height = image_data.get("height", 0)

                # Get colorspace
                colorspace_int = image_data.get("colorspace", 3)
                colorspace = self._parse_colorspace(colorspace_int)

                # Encode to base64
                base64_data = self._encode_image_base64(image_bytes)

                # Find bbox (use first available or estimate)
                bbox = [0, 0, width, height]
                if image_bboxes:
                    bbox = list(image_bboxes.values())[min(img_index, len(image_bboxes) - 1)]

                # Check if OCR needed
                should_ocr = self._should_perform_ocr(page, page_text_length, bbox, page.rect)
                ocr_text = None
                is_ocr_processed = False

                if should_ocr and self.ocr_enabled:
                    ocr_text = self.perform_ocr(page)
                    is_ocr_processed = True

                # Create block ID
                block_id = f"p{page_num + 1}_img{img_index}"

                # Build image block
                image_block = {
                    "block_id": block_id,
                    "block_type": BLOCK_TYPE_IMAGE,
                    "bbox": bbox_dict(*bbox),
                    "z_index": 0,  # Will be assigned later
                    "data": {
                        "type": BLOCK_TYPE_IMAGE,
                        "image_data": base64_data,
                        "image_format": image_format,
                        "width": width,
                        "height": height,
                        "dpi": None,  # Not available from PyMuPDF extract_image
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

    def _encode_image_base64(self, image_bytes: bytes) -> str:
        """
        Encode image bytes to base64 string.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Base64 encoded string
        """
        return base64.b64encode(image_bytes).decode('utf-8')

    def _should_perform_ocr(self, page, text_length: int, image_bbox: list, page_rect) -> bool:
        """
        Determine if OCR should be performed on this page.

        Args:
            page: PyMuPDF page object
            text_length: Length of extractable text on page
            image_bbox: Image bounding box
            page_rect: Page rectangle

        Returns:
            True if OCR should be performed
        """
        # If plenty of text, skip OCR
        if text_length >= MIN_TEXT_FOR_NO_OCR:
            return False

        # Calculate image area vs page area
        img_width = image_bbox[2] - image_bbox[0]
        img_height = image_bbox[3] - image_bbox[1]
        img_area = img_width * img_height

        page_area = page_rect.width * page_rect.height

        if page_area > 0:
            area_ratio = img_area / page_area
            # If image covers > 50% of page and little text, likely scanned
            if area_ratio > LARGE_IMAGE_THRESHOLD:
                return True

        return False

    def perform_ocr(self, page) -> Optional[str]:
        """
        Perform OCR on a page.

        Args:
            page: PyMuPDF page object

        Returns:
            Extracted OCR text or None if failed
        """
        try:
            import pytesseract
            from PIL import Image
            import io

            # Convert page to image
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")

            # Open with PIL
            image = Image.open(io.BytesIO(img_data))

            # Perform OCR
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
        """
        Parse colorspace from PyMuPDF integer.

        Args:
            colorspace_int: Colorspace integer (1=Gray, 3=RGB, 4=CMYK)

        Returns:
            Colorspace string
        """
        colorspace_map = {
            1: COLORSPACE_GRAY,
            3: COLORSPACE_RGB,
            4: COLORSPACE_CMYK
        }
        return colorspace_map.get(colorspace_int, COLORSPACE_RGB)

    def get_warnings(self) -> List[dict]:
        """Get accumulated warnings."""
        return self.warnings
