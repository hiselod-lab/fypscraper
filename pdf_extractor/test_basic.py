#!/usr/bin/env python3
"""
Basic test script to verify PDF extractor functionality.
"""

import pymupdf as fitz  # PyMuPDF
from pdf_extractor import PDFExtractor

# Create a simple test PDF
print("Creating test PDF...")
doc = fitz.open()
page = doc.new_page(width=612, height=792)  # Letter size

# Add some text
page.insert_text((72, 72), "Sample PDF Document", fontsize=24)
page.insert_text((72, 120), "This is a test document with some text.", fontsize=12)
page.insert_text((72, 150), "It contains multiple lines.", fontsize=12)

# Add a rectangle (shape)
page.draw_rect(fitz.Rect(72, 200, 300, 250), color=(0, 0, 1), width=2)

# Save test PDF
test_pdf_path = "/workspace/cmh35qc2s008uqyi6kgcyt1f8/pdf_extractor/test_sample.pdf"
doc.save(test_pdf_path)
doc.close()
print(f"Created test PDF: {test_pdf_path}")

# Test extraction
print("\nTesting PDF extraction...")
try:
    extractor = PDFExtractor(test_pdf_path, {"verbose": True, "ocr_enabled": False})

    print("\nExtracting to JSON...")
    output_path = extractor.extract_to_file()

    print(f"\nSuccess! Output saved to: {output_path}")

    # Show some stats
    print(f"Processing time: {extractor.end_time - extractor.start_time:.2f}s")
    print(f"Pages processed: {len(extractor.pages)}")
    print(f"Fonts registered: {extractor.font_registry.font_count()}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
