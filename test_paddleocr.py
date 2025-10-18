#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test PaddleOCR quality on VCR document
Compares original Docling output vs PaddleOCR extraction
"""

import os
from pathlib import Path

print("="*70)
print("PaddleOCR Quality Test")
print("="*70)

# Step 1: Find the original PDF
raw_dir = Path("rag_indexer/data/raw")
pdf_files = list(raw_dir.glob("*.pdf"))

if not pdf_files:
    print("ERROR: No PDF files found in rag_indexer/data/raw/")
    exit(1)

# Use first PDF (VCR)
pdf_path = pdf_files[0]
print(f"\nTesting with: {pdf_path.name}")

# Step 2: Convert PDF to images using PyMuPDF (no external dependencies needed)
print("\n1. Converting PDF to images...")
try:
    import fitz  # PyMuPDF
    from PIL import Image

    # Open PDF
    doc = fitz.open(str(pdf_path))
    print(f"   PDF has {len(doc)} page(s)")

    # Convert first page to image
    page = doc[0]

    # Render page at high resolution (300 DPI)
    zoom = 300 / 72  # 72 DPI is default
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Save as image
    test_image_path = "test_page.png"
    pix.save(test_image_path)

    print(f"   Saved test image: {test_image_path}")
    print(f"   Image size: {pix.width}x{pix.height} pixels")

    doc.close()

except ImportError:
    print("   ERROR: PyMuPDF not installed")
    print("   Run: pip install pymupdf")
    exit(1)
except Exception as e:
    print(f"   ERROR: Failed to convert PDF: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 3: Run PaddleOCR
print("\n2. Running PaddleOCR...")
try:
    from paddleocr import PaddleOCR

    # Initialize OCR (English only)
    # Note: PaddleOCR 3.x changed parameter names
    ocr = PaddleOCR(
        use_textline_orientation=True,  # Detect text orientation
        lang='en'                        # English only
    )

    print("   OCR initialized successfully")

    # Process first page
    result = ocr.predict(test_image_path)

    # Extract text with confidence scores
    extracted_lines = []
    total_confidence = 0

    # PaddleOCR 3.x returns different format
    if result and 'dt_polys' in result and 'rec_text' in result:
        extracted_lines = result['rec_text']
        confidences = result.get('rec_score', [])

        if confidences:
            total_confidence = sum(confidences)
            avg_confidence = total_confidence / len(confidences)
        else:
            avg_confidence = 0

        print(f"   Extracted {len(extracted_lines)} text lines")
        if avg_confidence > 0:
            print(f"   Average confidence: {avg_confidence:.2%}")
    else:
        print(f"   WARNING: Unexpected result format: {type(result)}")

except ImportError:
    print("   ERROR: PaddleOCR not installed")
    print("   Run: pip install paddlepaddle paddleocr")
    exit(1)
except Exception as e:
    print(f"   ERROR: OCR failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 4: Compare with Docling output
print("\n3. Comparing with Docling output...")

markdown_path = Path("rag_indexer/data/markdown") / pdf_path.stem
markdown_file = markdown_path.with_suffix('.md')

if markdown_file.exists():
    with open(markdown_file, 'r', encoding='utf-8') as f:
        docling_text = f.read()

    print(f"   Docling output: {len(docling_text)} chars")
else:
    print("   WARNING: Docling output not found")
    docling_text = ""

# Step 5: Display results
print("\n" + "="*70)
print("RESULTS COMPARISON")
print("="*70)

print("\n--- PaddleOCR Output ---")
paddleocr_text = '\n'.join(extracted_lines)
print(paddleocr_text)
print(f"\nTotal: {len(paddleocr_text)} chars")

if docling_text:
    print("\n" + "="*70)
    print("--- Docling Output ---")
    print(docling_text)
    print(f"\nTotal: {len(docling_text)} chars")

# Step 6: Analysis
print("\n" + "="*70)
print("ANALYSIS")
print("="*70)

if docling_text:
    # Check if texts are similar
    docling_words = set(docling_text.lower().split())
    paddle_words = set(paddleocr_text.lower().split())

    common_words = docling_words & paddle_words
    similarity = len(common_words) / max(len(docling_words), len(paddle_words))

    print(f"Word overlap: {similarity:.1%}")
    print(f"Docling unique words: {len(docling_words - paddle_words)}")
    print(f"PaddleOCR unique words: {len(paddle_words - docling_words)}")

# Check for <!-- image --> placeholders in Docling
if '<!-- image -->' in docling_text:
    print("\nWARNING: Docling output contains image placeholders")
    print("This confirms that Docling did NOT extract text from images")
else:
    print("\nDocling successfully extracted text (no image placeholders)")

print("\n" + "="*70)
print("RECOMMENDATION")
print("="*70)

if extracted_lines:
    print("PaddleOCR successfully extracted text from the PDF image")
    print(f"Average confidence: {avg_confidence:.2%}")

    if avg_confidence > 0.90:
        print("Quality: EXCELLENT - Ready for production use")
    elif avg_confidence > 0.80:
        print("Quality: GOOD - Suitable for most use cases")
    elif avg_confidence > 0.70:
        print("Quality: ACCEPTABLE - May need manual review")
    else:
        print("Quality: POOR - Consider improving image quality or trying different OCR")
else:
    print("ERROR: No text extracted by PaddleOCR")

print("="*70)
