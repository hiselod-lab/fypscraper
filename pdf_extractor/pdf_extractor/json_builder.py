"""
JSON assembly and serialization.
"""

import json
from typing import Dict, List
from .config import JSON_INDENT


class JSONBuilder:
    """
    Builds and serializes the final JSON structure.
    """

    @staticmethod
    def build(metadata: dict, pages: List[dict], fonts: dict, extraction_meta: dict) -> dict:
        """
        Assemble the complete JSON structure.

        Args:
            metadata: Document metadata
            pages: List of page dictionaries
            fonts: Font registry dictionary
            extraction_meta: Extraction metadata

        Returns:
            Complete document dictionary
        """
        return {
            "document_metadata": metadata,
            "fonts": fonts,
            "pages": pages,
            "extraction_metadata": extraction_meta
        }

    @staticmethod
    def serialize(data: dict, output_path: str, pretty: bool = True) -> None:
        """
        Write JSON to file.

        Args:
            data: Dictionary to serialize
            output_path: Output file path
            pretty: Whether to format with indentation

        Raises:
            IOError: If file write fails
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=JSON_INDENT, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to write JSON file: {e}")

    @staticmethod
    def to_json_string(data: dict, pretty: bool = True) -> str:
        """
        Convert dictionary to JSON string.

        Args:
            data: Dictionary to serialize
            pretty: Whether to format with indentation

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(data, indent=JSON_INDENT, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)
