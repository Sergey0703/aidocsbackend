#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main script for converting documents to markdown using Docling
Entry point for Part 1: Document → Markdown conversion
"""

import sys
import time
from datetime import datetime

from docling_processor import (
    get_docling_config,
    create_document_scanner,
    create_document_converter
)


def main(incremental=False):
    """
    Main conversion function
    
    Args:
        incremental: If True, skip already converted files
    
    Returns:
        bool: True if successful
    """
    print("=" * 70)
    print("📄 DOCLING DOCUMENT CONVERTER")
    print("=" * 70)
    print("Converting: Raw Documents → Markdown")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Load configuration
        print("\n🔧 Loading configuration...")
        config = get_docling_config()
        config.print_config()
        
        # Create scanner
        print("\n📂 Scanning for documents...")
        scanner = create_document_scanner(config)
        files_to_process = scanner.scan_directory()
        
        if not files_to_process:
            print("\n⚠️ No files found to convert")
            return False
        
        # Filter already converted (if incremental)
        if incremental:
            files_to_process = scanner.filter_already_converted(
                files_to_process, 
                incremental=True
            )
            
            if not files_to_process:
                print("\n✅ All files already converted")
                return True
        
        # Create converter
        print("\n🔄 Initializing converter...")
        converter = create_document_converter(config)
        
        # Convert documents
        results = converter.convert_batch(files_to_process)
        
        # Print final statistics
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n" + "=" * 70)
        print(f"✅ CONVERSION FINISHED")
        print(f"=" * 70)
        print(f"⏱️ Total time: {total_time/60:.1f} minutes")
        print(f"📊 Files processed: {results['total_files']}")
        print(f"   ✅ Successful: {results['successful']}")
        print(f"   ❌ Failed: {results['failed']}")
        
        if results['successful'] > 0:
            avg_time = results['total_time'] / results['successful']
            print(f"   ⚡ Average: {avg_time:.2f}s per file")
        
        print(f"\n📁 Output directory: {config.MARKDOWN_OUTPUT_DIR}")
        print(f"📋 Metadata directory: {config.METADATA_DIR}")
        
        if results['failed'] > 0:
            print(f"\n⚠️ Some files failed to convert")
            print(f"   Check: {config.FAILED_CONVERSIONS_DIR}")
        
        print(f"=" * 70)
        
        # Next steps
        print(f"\n🚀 Next step: Run indexer to create vectors")
        print(f"   python indexer.py")
        
        return results['failed'] == 0
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Conversion interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert documents to markdown using Docling"
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Skip already converted files'
    )
    parser.add_argument(
        '--input',
        type=str,
        help='Input directory (overrides config)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output directory (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Override config if needed
    if args.input:
        import os
        os.environ['RAW_DOCUMENTS_DIR'] = args.input
    
    if args.output:
        import os
        os.environ['MARKDOWN_OUTPUT_DIR'] = args.output
    
    # Run conversion
    success = main(incremental=args.incremental)
    
    sys.exit(0 if success else 1)