#!/usr/bin/env python3
"""
Diagnostic script to test Docling 2.55.1 directly
"""

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
import traceback

print("Testing Docling 2.55.1 configuration...\n")

# Test 1: Basic converter
print("=" * 60)
print("Test 1: Creating basic converter")
print("=" * 60)
try:
    converter = DocumentConverter()
    print("✅ Basic converter created successfully\n")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()
    print()

# Test 2: Converter with allowed formats
print("=" * 60)
print("Test 2: Creating converter with allowed formats")
print("=" * 60)
try:
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF]
    )
    print("✅ Converter with formats created successfully\n")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()
    print()

# Test 3: Check PdfPipelineOptions attributes
print("=" * 60)
print("Test 3: Inspecting PdfPipelineOptions")
print("=" * 60)
try:
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    
    options = PdfPipelineOptions()
    
    print(f"Available attributes in PdfPipelineOptions:")
    for attr in dir(options):
        if not attr.startswith('_'):
            try:
                value = getattr(options, attr)
                if not callable(value):
                    print(f"  - {attr}: {value}")
            except:
                print(f"  - {attr}: <property>")
    print()
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()
    print()

# Test 4: Try to convert a file
print("=" * 60)
print("Test 4: Attempting file conversion")
print("=" * 60)
try:
    import sys
    from pathlib import Path
    
    # Check if file exists
    test_file = Path("./data/raw/Order1vert.pdf")
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
    else:
        print(f"📄 Test file: {test_file}")
        print(f"   Size: {test_file.stat().st_size} bytes")
        
        converter = DocumentConverter()
        print("   Converting...")
        result = converter.convert(str(test_file))
        
        markdown = result.document.export_to_markdown()
        print(f"✅ Conversion successful!")
        print(f"   Markdown length: {len(markdown)} chars")
        print(f"   First 200 chars: {markdown[:200]}")
        
except Exception as e:
    print(f"❌ Conversion failed: {e}")
    traceback.print_exc()
    print()

print("=" * 60)
print("Diagnostic complete")
print("=" * 60)