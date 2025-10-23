"""
Command-line interface for PDF Extractor.
"""

import sys
import argparse
from .extractor import PDFExtractor, PDFExtractionError, VERSION


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pdf-extractor",
        description="Extract PDF content to structured JSON with layout preservation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdf-extractor document.pdf
  pdf-extractor document.pdf -o output.json
  pdf-extractor scanned.pdf --ocr-lang eng+ara
  pdf-extractor document.pdf --no-ocr --no-tables -v
        """
    )

    # Positional arguments
    parser.add_argument(
        "input_pdf",
        help="Path to input PDF file"
    )

    # Optional arguments
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: <input>_extracted.json)",
        default=None
    )

    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR for scanned PDFs"
    )

    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Disable table detection and extraction"
    )

    parser.add_argument(
        "--no-shapes",
        action="store_true",
        help="Disable shape/line extraction"
    )

    parser.add_argument(
        "--ocr-lang",
        default="eng",
        help="OCR language (default: eng, use eng+ara for multiple)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"pdf-extractor {VERSION}"
    )

    # Parse arguments
    args = parser.parse_args()

    # Build options
    options = {
        "ocr_enabled": not args.no_ocr,
        "ocr_language": args.ocr_lang,
        "table_detection_enabled": not args.no_tables,
        "shape_extraction_enabled": not args.no_shapes,
        "verbose": args.verbose
    }

    # Run extraction
    try:
        if args.verbose:
            print(f"PDF Extractor v{VERSION}")
            print(f"Input: {args.input_pdf}")
            print()

        # Initialize extractor
        extractor = PDFExtractor(args.input_pdf, options)

        # Extract to file
        output_path = extractor.extract_to_file(args.output)

        print(f"Extraction successful!")
        print(f"Output: {output_path}")

        # Show statistics if verbose
        if args.verbose:
            print()
            print("Statistics:")
            print(f"  Processing time: {extractor.end_time - extractor.start_time:.2f}s")
            if extractor.warnings:
                print(f"  Warnings: {len(extractor.warnings)}")

        sys.exit(0)

    except PDFExtractionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    except IOError as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(3)

    except KeyboardInterrupt:
        print("\nExtraction interrupted by user", file=sys.stderr)
        sys.exit(130)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
