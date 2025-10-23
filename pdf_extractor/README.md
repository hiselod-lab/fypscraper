# PDF Extractor

A simple, powerful Python tool for extracting PDF content with complete layout preservation. Converts PDFs to structured JSON format suitable for LLM processing and PDF regeneration.

## Key Features

- **Layout Preservation:** Captures exact positioning, fonts, colors, and styling
- **Universal Support:** Handles any PDF length, language, or structure
- **Comprehensive Extraction:** Text, images, tables, shapes with precise bounding boxes
- **OCR Support:** Tesseract integration for scanned documents
- **Self-Contained Output:** Images embedded as base64, no external dependencies
- **Fast Performance:** Optimized extraction pipeline with optional features
- **LLM-Ready:** JSON structure designed for AI processing and PDF regeneration
- **Simple Code:** Single-file architecture for easy understanding and modification

## Installation

### Prerequisites

1. Python 3.9 or higher
2. Tesseract-OCR (for scanned PDF support)

**Install Tesseract:**
- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
- **macOS:** `brew install tesseract`
- **Windows:** Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

### Install PDF Extractor

```bash
# Clone or navigate to the directory
cd pdf_extractor

# Install in development mode
pip install -e .

# Or install for use
pip install .
```

## Quick Start

```bash
# Basic extraction
pdf-extractor document.pdf

# Custom output path
pdf-extractor document.pdf -o output.json

# Extract with specific OCR language
pdf-extractor scanned.pdf --ocr-lang ara

# Disable OCR for faster processing
pdf-extractor document.pdf --no-ocr
```

**Python API:**
```python
from pdf_extractor import PDFExtractor

# Extract to dictionary
extractor = PDFExtractor("document.pdf")
data = extractor.extract()

# Extract to file
output_path = extractor.extract_to_file("output.json")
print(f"Extracted to {output_path}")
```

## Command Line Usage

```bash
usage: pdf-extractor [-h] [-o OUTPUT] [--no-ocr] [--no-tables] [--no-shapes]
                     [--ocr-lang LANG] [-v] [--version]
                     input_pdf

positional arguments:
  input_pdf             Path to input PDF file

optional arguments:
  -h, --help            Show help message
  -o OUTPUT, --output OUTPUT
                        Output JSON file path (default: <input>_extracted.json)
  --no-ocr              Disable OCR for scanned PDFs
  --no-tables           Disable table detection and extraction
  --no-shapes           Disable shape/line extraction
  --ocr-lang LANG       OCR language (default: eng, use eng+ara for multiple)
  -v, --verbose         Enable verbose logging with performance stats
  --version             Show version and exit
```

**Examples:**
```bash
# Extract invoice with tables
pdf-extractor invoice.pdf

# Extract multilingual document (English + Arabic)
pdf-extractor document.pdf --ocr-lang eng+ara

# Fast extraction (skip expensive features)
pdf-extractor large_document.pdf --no-ocr --no-shapes

# Verbose output with performance metrics
pdf-extractor document.pdf -v
```

## Output JSON Structure

The extracted JSON contains four main sections:

1. **document_metadata:** PDF properties (title, author, page count, etc.)
2. **fonts:** Global font registry with all fonts used in document
3. **pages:** Array of page objects with content blocks
4. **extraction_metadata:** Processing info (timestamp, warnings, statistics)

**Page content blocks:**
- **text:** Text with font, size, color, position
- **image:** Embedded images as base64 with dimensions
- **table:** Structured table data with cells, borders, formatting
- **shape:** Lines, rectangles, curves with styling

**Example structure:**
```json
{
  "document_metadata": {
    "title": "Sample Document",
    "page_count": 10,
    "pdf_version": "1.7"
  },
  "fonts": {
    "f_abc12345": {
      "name": "Arial-Bold",
      "family": "Arial",
      "is_bold": true,
      "is_italic": false
    }
  },
  "pages": [
    {
      "page_number": 1,
      "dimensions": {"width": 612.0, "height": 792.0, "rotation": 0},
      "content_blocks": [
        {
          "block_id": "p1_b1",
          "block_type": "text",
          "bbox": {"x0": 72, "y0": 72, "x1": 540, "y1": 100},
          "z_index": 3001,
          "data": {
            "type": "text",
            "lines": [
              {
                "bbox": {"x0": 72, "y0": 72, "x1": 200, "y1": 90},
                "spans": [
                  {
                    "text": "Sample Text",
                    "font_id": "f_abc12345",
                    "font_size": 24.0,
                    "color": {"r": 0, "g": 0, "b": 0, "hex": "#000000"}
                  }
                ]
              }
            ]
          }
        }
      ]
    }
  ],
  "extraction_metadata": {
    "extractor_version": "1.0.0",
    "extraction_timestamp": "2025-10-23T12:00:00Z",
    "processing_time": 5.2,
    "statistics": {
      "total_text_blocks": 120,
      "total_images": 5,
      "total_tables": 3,
      "fonts_used": 8
    }
  }
}
```

## Use Cases

**1. LLM-Based PDF Analysis**
- Extract PDF to JSON
- Process with LLM for summarization, translation, data extraction
- Regenerate PDF from modified JSON

**2. PDF Archival and Search**
- Convert PDFs to searchable JSON
- Index content for full-text search
- Preserve original layout for accurate viewing

**3. Document Conversion**
- PDF → JSON → HTML/Markdown/DOCX
- Maintain formatting and structure
- Extract tables for spreadsheet analysis

**4. Automated Data Extraction**
- Extract tables from invoices, reports, forms
- Structured JSON output for database import
- Batch processing for large document sets

**5. Accessibility**
- Extract text with reading order
- OCR scanned documents
- Provide structured format for screen readers

## Performance

**Typical benchmarks:**
- Text-based document: 0.5-1 second per page
- Scanned document (with OCR): 2-3 seconds per page
- Complex document (tables, shapes): 1.5-2.5 seconds per page

**Performance tips:**
- Disable OCR if not needed (--no-ocr): Saves 1-3 seconds per scanned page
- Disable table detection for simple documents (--no-tables): Saves ~0.2s per page
- Use verbose mode (-v) to see performance breakdown

## Troubleshooting

**Error: "Tesseract not found"**
- Install Tesseract-OCR binary (see Installation section)
- Verify installation: `tesseract --version`

**Error: "Invalid or corrupted PDF file"**
- PDF may be damaged or encrypted
- Try opening PDF in a viewer to verify it's readable
- For encrypted PDFs, decrypt first with password

**Error: "Out of memory"**
- PDF has many large images
- Try processing with --no-ocr to skip image processing
- Consider splitting PDF into smaller files

**Warning: "Table detection uncertain"**
- Complex or borderless tables may not be detected perfectly
- Tables will be extracted as text blocks instead
- Verify output JSON and adjust table detection settings if needed

**Performance issues:**
- Use --no-ocr for non-scanned documents
- Use --no-shapes to skip shape extraction
- Check verbose output (-v) to identify bottlenecks

## Project Structure

```
pdf_extractor/
├── README.md                    # This file
├── requirements.txt             # Dependencies
├── setup.py                     # Package setup
├── .gitignore                   # Git ignore rules
├── examples/                    # Sample PDFs and outputs
├── tests/                       # Test suite
│   ├── __init__.py
│   └── test_*.py
└── pdf_extractor/              # Main package (simplified!)
    ├── __init__.py             # Package exports
    ├── __main__.py             # CLI entry point
    └── extractor.py            # Complete extraction pipeline (single file!)
```

**Simplified Architecture:** All extraction logic is consolidated into a single, easy-to-navigate `extractor.py` file (~1,270 lines). This makes the codebase simple to understand, modify, and debug.

## Code Overview

The `extractor.py` file contains everything in logical sections:

1. **Configuration:** All constants and settings
2. **Utilities:** Helper functions for colors, fonts, validation
3. **FontRegistry:** Global font management
4. **Processors:** Text, Image, Table, and Shape extraction classes
5. **JSONBuilder:** Output serialization
6. **PDFExtractor:** Main orchestrator class

This single-file design means:
- Easy to understand the full pipeline
- Simple to modify behavior
- No jumping between multiple files
- Clear code organization with section markers

## Contributing

Contributions welcome! The simplified structure makes it easy to add features or fix bugs.

**Development setup:**
```bash
# Clone or navigate to directory
cd pdf_extractor
pip install -e .
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=pdf_extractor tests/
```

**To add features:**
1. Open `pdf_extractor/extractor.py` - everything is here!
2. Find the relevant section (clearly marked with headers)
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [PyMuPDF](https://pymupdf.readthedocs.io/)
- Table detection via [pdfplumber](https://github.com/jsvine/pdfplumber)
- OCR powered by [Tesseract](https://github.com/tesseract-ocr/tesseract)

## Support

For issues or questions, please open an issue on GitHub.
