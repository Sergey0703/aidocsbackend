"""
Test Script for Storage Workflow

This script tests the complete Storage workflow:
1. Upload a test document
2. Verify it appears in pending
3. Process it (convert to markdown)
4. Verify it moved to processed

Usage:
    python test_storage_workflow.py /path/to/test/document.pdf
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.storage_manager import SupabaseStorageManager
from chunking_vectors.registry_manager import DocumentRegistryManager
from docling_processor.config_docling import DoclingConfig
from docling_processor.document_converter import DocumentConverter
from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_storage_workflow(test_file_path: str):
    """
    Test complete Storage workflow.

    Args:
        test_file_path: Path to a test document (PDF, DOCX, or PPTX)
    """
    print("=" * 60)
    print("TESTING STORAGE WORKFLOW")
    print("=" * 60)

    test_file = Path(test_file_path)
    if not test_file.exists():
        print(f"[-] Error: Test file not found: {test_file_path}")
        sys.exit(1)

    print(f"\n[*] Test file: {test_file.name}")
    print(f"   Size: {test_file.stat().st_size / 1024:.2f} KB")

    # ================================================
    # Step 1: Initialize Managers
    # ================================================

    print("\n[STEP 1] Initializing managers...")

    connection_string = os.getenv('SUPABASE_CONNECTION_STRING')
    if not connection_string:
        print("[-] ERROR: SUPABASE_CONNECTION_STRING not set")
        sys.exit(1)

    try:
        storage_manager = SupabaseStorageManager()
        registry_manager = DocumentRegistryManager(connection_string)
        print("[+] Managers initialized")
    except Exception as e:
        print(f"[-] Failed to initialize: {e}")
        sys.exit(1)

    # ================================================
    # Step 2: Upload Test Document
    # ================================================

    print("\n[STEP 2] Uploading test document to Storage...")

    try:
        upload_result = storage_manager.upload_document(
            file=str(test_file),
            original_filename=test_file.name,
            target_folder='raw/pending'
        )

        print(f"[+] Uploaded successfully")
        print(f"   Storage path: {upload_result['storage_path']}")
        print(f"   File size: {upload_result['file_size']} bytes")

    except Exception as e:
        print(f"[-] Upload failed: {e}")
        sys.exit(1)

    # ================================================
    # Step 3: Create Registry Entry
    # ================================================

    print("\n[STEP 3] Creating registry entry...")

    try:
        registry_id = registry_manager.create_entry_from_storage(
            storage_path=upload_result['storage_path'],
            original_filename=upload_result['original_filename'],
            file_size=upload_result['file_size'],
            content_type=upload_result['content_type']
        )

        if registry_id:
            print(f"[+] Registry entry created")
            print(f"   Registry ID: {registry_id}")
        else:
            print("[-] Failed to create registry entry")
            sys.exit(1)

    except Exception as e:
        print(f"[-] Registry creation failed: {e}")
        sys.exit(1)

    # ================================================
    # Step 4: Verify Pending Status
    # ================================================

    print("\n[STEP 4] Verifying document is pending...")

    try:
        pending_docs = registry_manager.get_pending_documents(limit=100)
        found = any(doc['id'] == registry_id for doc in pending_docs)

        if found:
            print(f"[+] Document found in pending queue")
            print(f"   Total pending documents: {len(pending_docs)}")
        else:
            print("[-] Document not found in pending queue!")
            sys.exit(1)

    except Exception as e:
        print(f"[-] Verification failed: {e}")
        sys.exit(1)

    # ================================================
    # Step 5: Process Document (Convert)
    # ================================================

    print("\n[STEP 5] Processing document (conversion)...")

    try:
        config = DoclingConfig()
        converter = DocumentConverter(
            config,
            enable_ocr_enhancement=False,  # Disable OCR for faster testing
            storage_manager=storage_manager,
            registry_manager=registry_manager
        )

        # Get document record
        doc_record = registry_manager.get_document_by_storage_path(upload_result['storage_path'])

        if not doc_record:
            print("[-] Could not retrieve document record!")
            sys.exit(1)

        # Convert
        success, output_path, error_msg = converter.convert_from_storage(doc_record)

        if success:
            print(f"[+] Conversion successful")
            print(f"   Markdown path: {output_path}")
        else:
            print(f"[-] Conversion failed: {error_msg}")
            sys.exit(1)

    except Exception as e:
        print(f"[-] Processing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ================================================
    # Step 6: Verify Processed Status
    # ================================================

    print("\n[STEP 6] Verifying document was processed...")

    try:
        # Wait a moment for DB to update
        time.sleep(1)

        # Retrieve updated record
        updated_doc = registry_manager.get_document_by_storage_path(
            upload_result['storage_path'].replace('raw/pending/', 'raw/processed/')
        )

        if updated_doc:
            print(f"[+] Document successfully processed")
            print(f"   New storage path: {updated_doc['storage_path']}")
            print(f"   Storage status: {updated_doc['storage_status']}")
            print(f"   Markdown path: {updated_doc.get('markdown_file_path', 'N/A')}")

            # Verify markdown file exists
            if updated_doc.get('markdown_file_path'):
                md_path = Path(updated_doc['markdown_file_path'])
                if md_path.exists():
                    print(f"   Markdown file size: {md_path.stat().st_size / 1024:.2f} KB")
                else:
                    print(f"   [!] Warning: Markdown file not found on disk")
        else:
            print("[-] Document not found with processed status!")
            print("[!] Check if file is in raw/failed/ instead")
            sys.exit(1)

    except Exception as e:
        print(f"[-] Verification failed: {e}")
        sys.exit(1)

    # ================================================
    # Summary
    # ================================================

    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print(f"\n[*] Summary:")
    print(f"   ✓ Document uploaded to Storage")
    print(f"   ✓ Registry entry created")
    print(f"   ✓ Document converted to markdown")
    print(f"   ✓ Status updated to 'processed'")
    print(f"   ✓ File moved to processed folder")

    print(f"\n[*] Next steps:")
    print(f"   1. Check the markdown file:")
    print(f"      cat '{output_path}'")
    print(f"\n   2. Run indexing to create embeddings:")
    print(f"      python rag_indexer/indexer.py")
    print(f"\n   3. Clean up test data from Supabase:")
    print(f"      - Delete from document_registry WHERE id = '{registry_id}'")
    print(f"      - Delete from Storage: {updated_doc.get('storage_path', 'N/A')}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Test Storage workflow end-to-end'
    )

    parser.add_argument(
        'file',
        type=str,
        help='Path to test document (PDF, DOCX, or PPTX)'
    )

    args = parser.parse_args()

    test_storage_workflow(args.file)


if __name__ == '__main__':
    main()
