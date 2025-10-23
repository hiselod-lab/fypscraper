"""
Tests for utility functions.
"""

import pytest
from pdf_extractor.utils import (
    generate_output_filename,
    parse_font_family,
    generate_font_id,
    bbox_dict,
    color_dict,
    parse_color_int,
    calculate_alignment
)


def test_generate_output_filename():
    """Test output filename generation."""
    result = generate_output_filename("document.pdf")
    assert result == "document_extracted.json"


def test_parse_font_family():
    """Test font family parsing."""
    assert parse_font_family("Arial-BoldMT") == "Arial"
    assert parse_font_family("TimesNewRoman-Bold") == "TimesNewRoman"
    assert parse_font_family("Helvetica") == "Helvetica"


def test_generate_font_id():
    """Test font ID generation."""
    font_id = generate_font_id("Arial")
    assert font_id.startswith("f_")
    assert len(font_id) == 10  # f_ + 8 chars

    # Same font name should generate same ID
    font_id2 = generate_font_id("Arial")
    assert font_id == font_id2


def test_bbox_dict():
    """Test bounding box dictionary creation."""
    bbox = bbox_dict(10.5, 20.3, 100.7, 200.9)
    assert bbox["x0"] == 10.5
    assert bbox["y0"] == 20.3
    assert bbox["x1"] == 100.7
    assert bbox["y1"] == 200.9


def test_color_dict():
    """Test color dictionary creation."""
    color = color_dict(255, 128, 0)
    assert color["r"] == 255
    assert color["g"] == 128
    assert color["b"] == 0
    assert color["hex"] == "#ff8000"


def test_parse_color_int():
    """Test color integer parsing."""
    # Black (0x000000)
    color = parse_color_int(0)
    assert color["r"] == 0
    assert color["g"] == 0
    assert color["b"] == 0

    # White (0xFFFFFF)
    color = parse_color_int(16777215)
    assert color["r"] == 255
    assert color["g"] == 255
    assert color["b"] == 255


def test_calculate_alignment():
    """Test text alignment calculation."""
    # Left aligned
    assert calculate_alignment(10, 50, 10, 100) == "left"

    # Center aligned
    assert calculate_alignment(30, 70, 10, 90) == "center"

    # Right aligned
    assert calculate_alignment(60, 100, 10, 100) == "right"
