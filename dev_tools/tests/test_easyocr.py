#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test EasyOCR quality on VCR document
Compares original Docling output vs EasyOCR extraction
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding issues
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

print("="*70)
print("EasyOCR Quality Test")
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

# Step 2: Convert PDF to image using PyMuPDF
print("\n1. Converting PDF to image...")
try:
    import fitz  # PyMuPDF

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
    test_image_path = "test_page_easy.png"
    pix.save(test_image_path)

    print(f"   Saved test image: {test_image_path}")
    print(f"   Image size: {pix.width}x{pix.height} pixels")

    doc.close()

except Exception as e:
    print(f"   ERROR: Failed to convert PDF: {e}")
    exit(1)

# Step 3: Run EasyOCR
print("\n2. Running EasyOCR...")
try:
    import easyocr

    # Initialize OCR (English only, GPU optional)
    print("   Initializing EasyOCR (this may take a moment)...")
    reader = easyocr.Reader(['en'], gpu=False)  # Use CPU

    print("   OCR initialized successfully")

    # Process image
    print("   Processing image...")
    result = reader.readtext(test_image_path)

    # Extract text with confidence scores
    extracted_lines = []
    total_confidence = 0

    for (bbox, text, confidence) in result:
        extracted_lines.append(text)
        total_confidence += confidence

    avg_confidence = total_confidence / len(result) if result else 0

    print(f"   Extracted {len(extracted_lines)} text regions")
    print(f"   Average confidence: {avg_confidence:.2%}")

except ImportError:
    print("   ERROR: EasyOCR not installed")
    print("   Run: pip install easyocr")
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

print("\n--- EasyOCR Output ---")
easyocr_text = '\n'.join(extracted_lines)
print(easyocr_text)
print(f"\nTotal: {len(easyocr_text)} chars, {len(extracted_lines)} lines")

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
    easy_words = set(easyocr_text.lower().split())

    common_words = docling_words & easy_words
    if len(docling_words) > 0 or len(easy_words) > 0:
        similarity = len(common_words) / max(len(docling_words), len(easy_words))
    else:
        similarity = 0

    print(f"Word overlap: {similarity:.1%}")
    print(f"Docling unique words: {len(docling_words - easy_words)}")
    print(f"EasyOCR unique words: {len(easy_words - docling_words)}")

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
    print(f"EasyOCR successfully extracted {len(extracted_lines)} text regions")
    print(f"Average confidence: {avg_confidence:.2%}")

    if avg_confidence > 0.90:
        print("Quality: EXCELLENT - Ready for production use")
    elif avg_confidence > 0.80:
        print("Quality: GOOD - Suitable for most use cases")
    elif avg_confidence > 0.70:
        print("Quality: ACCEPTABLE - May need manual review")
    else:
        print("Quality: POOR - Consider improving image quality")

    print(f"\nNext steps:")
    print(f"  1. If quality is good, integrate EasyOCR into pipeline")
    print(f"  2. Add OCR enhancement step after Docling conversion")
    print(f"  3. Replace <!-- image --> placeholders with OCR text")
else:
    print("ERROR: No text extracted by EasyOCR")

print("="*70)
