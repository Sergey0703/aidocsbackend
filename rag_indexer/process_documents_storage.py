#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Processing Pipeline - Storage Mode

This script processes documents from Supabase Storage instead of local filesystem.
It scans for pending documents in the database, downloads them, converts them to
markdown using Docling, and updates their status.

Usage:
    python process_documents_storage.py
    python process_documents_storage.py --limit 10
    python process_documents_storage.py --enable-ocr
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from docling_processor.config_docling import DoclingConfig
from docling_processor.document_scanner import create_document_scanner
from docling_processor.document_converter import DocumentConverter
from storage.storage_manager import SupabaseStorageManager
from chunking_vectors.registry_manager import DocumentRegistryManager

# Load environment variables
load_dotenv()


def main():
    """Main entry point for Storage-based document processing."""
    parser = argparse.ArgumentParser(
        description='Process documents from Supabase Storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all pending documents
  python process_documents_storage.py

  # Process only first 10 pending documents
  python process_documents_storage.py --limit 10

  # Enable OCR enhancement
  python process_documents_storage.py --enable-ocr

  # Use specific OCR strategy
  python process_documents_storage.py --enable-ocr --ocr-strategy gemini

  # Dry run (show what would be processed)
  python process_documents_storage.py --dry-run
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of documents to process (None = all pending)'
    )

    parser.add_argument(
        '--enable-ocr',
        action='store_true',
        help='Enable OCR enhancement for images'
    )

    parser.add_argument(
        '--ocr-strategy',
        type=str,
        choices=['easyocr', 'gemini', 'fallback', 'ensemble'],
        default='fallback',
        help='OCR strategy to use (default: fallback)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("DOCUMENT PROCESSING PIPELINE - STORAGE MODE")
    print("=" * 60)

    # ================================================
    # 1. Initialize Configuration
    # ================================================

    print("\n[*] Initializing configuration...")
    config = DoclingConfig()

    # ================================================
    # 2. Initialize Storage and Registry Managers
    # ================================================

    print("[*] Initializing Supabase Storage and Registry...")

    connection_string = os.getenv('SUPABASE_CONNECTION_STRING')
    if not connection_string:
        print("[-] ERROR: SUPABASE_CONNECTION_STRING not set in environment")
        sys.exit(1)

    try:
        storage_manager = SupabaseStorageManager()
        registry_manager = DocumentRegistryManager(connection_string)
    except Exception as e:
        print(f"[-] ERROR: Failed to initialize managers: {e}")
        sys.exit(1)

    # ================================================
    # 3. Scan for Pending Documents
    # ================================================

    print("\n[*] Scanning for pending documents...")

    scanner = create_document_scanner(config, registry_manager)
    pending_docs = scanner.scan_storage(limit=args.limit)

    if not pending_docs:
        print("[!] No pending documents found in Storage.")
        print("[*] Use 'python upload_documents.py' to upload documents first.")
        sys.exit(0)

    # ================================================
    # 4. Dry Run Check
    # ================================================

    if args.dry_run:
        print(f"\n[*] DRY RUN MODE - Would process {len(pending_docs)} documents:")
        for doc in pending_docs[:10]:  # Show first 10
            print(f"   - {doc['original_filename']} ({doc['file_size_bytes']} bytes)")
        if len(pending_docs) > 10:
            print(f"   ... and {len(pending_docs) - 10} more")
        print("\n[*] Run without --dry-run to actually process documents")
        sys.exit(0)

    # ================================================
    # 5. Initialize Converter with Storage Support
    # ================================================

    print("\n[*] Initializing document converter...")

    converter = DocumentConverter(
        config,
        enable_ocr_enhancement=args.enable_ocr,
        ocr_strategy=args.ocr_strategy,
        storage_manager=storage_manager,
        registry_manager=registry_manager
    )

    # ================================================
    # 6. Process Documents from Storage
    # ================================================

    print(f"\n[*] Processing {len(pending_docs)} documents from Storage...")

    stats = converter.convert_batch_from_storage(pending_docs)

    # ================================================
    # 7. Print Summary
    # ================================================

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)

    print(f"\n[*] Next steps:")
    print(f"   1. Run indexing pipeline to create vector embeddings:")
    print(f"      cd {Path(__file__).parent.parent}")
    print(f"      python rag_indexer/indexer.py")
    print(f"\n   2. Or use full pipeline (if markdown files need re-indexing):")
    print(f"      python rag_indexer/pipeline.py")

    # Exit with error code if any files failed
    if stats.get('failed', 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
