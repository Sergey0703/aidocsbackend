#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test document conversion with JSON output"""

import sys
from pathlib import Path

# Add rag_indexer to path
sys.path.insert(0, str(Path(__file__).parent / "rag_indexer"))

from docling_processor.config_docling import DoclingConfig
from docling_processor.document_converter import DocumentConverter

def main():
    print("=" * 60)
    print("DOCUMENT CONVERSION WITH JSON OUTPUT TEST")
    print("=" * 60)

    # Load config
    config = DoclingConfig()
    print(f"\nConfiguration loaded:")
    print(f"  Save JSON: {config.SAVE_JSON_OUTPUT}")
    print(f"  JSON dir: {config.JSON_OUTPUT_DIR}")
    print(f"  Markdown dir: {config.MARKDOWN_OUTPUT_DIR}")

    # Initialize converter
    print(f"\nInitializing converter...")
    converter = DocumentConverter(
        config=config,
        enable_ocr_enhancement=False  # Disable OCR for faster test
    )

    # Find a test file
    raw_dir = Path(config.RAW_DOCUMENTS_DIR)
    if not raw_dir.is_absolute():
        # Convert relative path to absolute based on project root
        raw_dir = (Path(__file__).parent / "rag_indexer" / config.RAW_DOCUMENTS_DIR).resolve()

    print(f"  Raw dir: {raw_dir}")
    print(f"  Exists: {raw_dir.exists()}")

    test_files = list(raw_dir.glob("*.pdf"))[:1]  # Just convert 1 file

    if not test_files:
        print(f"ERROR: No PDF files found in {raw_dir}")
        return False

    test_file = test_files[0]
    print(f"\nTest file: {test_file.name}")

    # Convert
    print(f"\nConverting...")
    success, output_path, error = converter.convert_file(test_file)

    if success:
        print(f"\nCONVERSION SUCCESSFUL!")
        print(f"  Markdown: {output_path}")

        # Check if JSON was created
        json_path = config.get_json_output_path(test_file)
        if json_path and json_path.exists():
            print(f"  JSON: {json_path}")
            print(f"  JSON size: {json_path.stat().st_size:,} bytes")
            print(f"\nJSON OUTPUT: SUCCESS")
        else:
            print(f"  JSON: NOT FOUND")
            print(f"\nJSON OUTPUT: FAILED")
        return True
    else:
        print(f"\nCONVERSION FAILED: {error}")
        return False

if __name__ == "__main__":
    main()
