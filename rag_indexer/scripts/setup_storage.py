#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supabase Storage Setup Script

This script automatically sets up the Supabase Storage bucket for the RAG system.
It creates the bucket if it doesn't exist and verifies the setup.

Usage:
    python setup_storage.py
    python setup_storage.py --verify-only
    python setup_storage.py --bucket-name custom-bucket
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client

# Load environment variables
load_dotenv()


class StorageSetup:
    """Setup and verify Supabase Storage configuration."""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        bucket_name: str = 'vehicle-documents'
    ):
        """
        Initialize Storage setup.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service role key
            bucket_name: Name of bucket to create
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.bucket_name = bucket_name
        self.client: Client = None

    def connect(self) -> bool:
        """
        Connect to Supabase.

        Returns:
            bool: True if connected successfully
        """
        try:
            print(f"[*] Connecting to Supabase...")
            print(f"    URL: {self.supabase_url}")

            self.client = create_client(self.supabase_url, self.supabase_key)

            # Test connection by listing buckets
            buckets = self.client.storage.list_buckets()

            print(f"[+] Connected successfully")
            print(f"    Existing buckets: {len(buckets)}")

            return True

        except Exception as e:
            print(f"[-] Connection failed: {e}")
            return False

    def bucket_exists(self) -> bool:
        """
        Check if bucket already exists.

        Returns:
            bool: True if bucket exists
        """
        try:
            buckets = self.client.storage.list_buckets()
            exists = any(b.name == self.bucket_name for b in buckets)

            if exists:
                print(f"[+] Bucket '{self.bucket_name}' already exists")
            else:
                print(f"[*] Bucket '{self.bucket_name}' does not exist")

            return exists

        except Exception as e:
            print(f"[-] Error checking bucket: {e}")
            return False

    def create_bucket(self) -> bool:
        """
        Create Storage bucket with appropriate settings.

        Returns:
            bool: True if created successfully
        """
        try:
            print(f"[*] Creating bucket '{self.bucket_name}'...")

            # Create bucket with settings
            response = self.client.storage.create_bucket(
                self.bucket_name,
                options={
                    'public': False,  # Private bucket
                    'file_size_limit': 52428800,  # 50 MB
                    'allowed_mime_types': [
                        'application/pdf',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'application/vnd.ms-powerpoint'
                    ]
                }
            )

            print(f"[+] Bucket created successfully")
            print(f"    Name: {self.bucket_name}")
            print(f"    Public: No (private)")
            print(f"    File size limit: 50 MB")

            return True

        except Exception as e:
            error_str = str(e)

            # Check if bucket already exists (not an error)
            if 'already exists' in error_str.lower() or '42P07' in error_str:
                print(f"[+] Bucket '{self.bucket_name}' already exists (not an error)")
                return True

            print(f"[-] Failed to create bucket: {e}")
            return False

    def create_folder_structure(self) -> bool:
        """
        Create folder structure in bucket by uploading placeholder files.

        Folders in Supabase Storage are created implicitly when files are uploaded.
        We upload .gitkeep files to create the folder structure.

        Returns:
            bool: True if successful
        """
        try:
            print(f"[*] Creating folder structure...")

            folders = [
                'raw/pending',
                'raw/processed',
                'raw/failed'
            ]

            # Create a small placeholder content
            placeholder = b'# This folder is managed by the RAG system\n'

            for folder in folders:
                try:
                    path = f"{folder}/.gitkeep"

                    # Upload placeholder file
                    self.client.storage.from_(self.bucket_name).upload(
                        path=path,
                        file=placeholder,
                        file_options={
                            'content-type': 'text/plain',
                            'upsert': 'true'  # Overwrite if exists
                        }
                    )

                    print(f"    [+] Created: {folder}/")

                except Exception as folder_error:
                    # If file already exists, that's OK
                    if 'already exists' in str(folder_error).lower():
                        print(f"    [+] Exists: {folder}/")
                    else:
                        print(f"    [!] Warning: Could not create {folder}/: {folder_error}")

            print(f"[+] Folder structure created")
            return True

        except Exception as e:
            print(f"[-] Failed to create folder structure: {e}")
            return False

    def verify_setup(self) -> bool:
        """
        Verify Storage setup is correct.

        Returns:
            bool: True if verification passed
        """
        print(f"\n[*] Verifying Storage setup...")

        checks_passed = 0
        checks_total = 0

        # Check 1: Bucket exists
        checks_total += 1
        try:
            buckets = self.client.storage.list_buckets()
            bucket = next((b for b in buckets if b.name == self.bucket_name), None)

            if bucket:
                print(f"    [✓] Bucket '{self.bucket_name}' exists")
                print(f"        Public: {bucket.public}")
                print(f"        ID: {bucket.id}")
                checks_passed += 1
            else:
                print(f"    [✗] Bucket '{self.bucket_name}' not found")

        except Exception as e:
            print(f"    [✗] Error checking bucket: {e}")

        # Check 2: Can list files
        checks_total += 1
        try:
            files = self.client.storage.from_(self.bucket_name).list()
            print(f"    [✓] Can list files in bucket")
            print(f"        Files/folders: {len(files)}")
            checks_passed += 1
        except Exception as e:
            print(f"    [✗] Cannot list files: {e}")

        # Check 3: Folder structure exists
        checks_total += 1
        try:
            folders_found = 0
            expected_folders = ['raw']

            files = self.client.storage.from_(self.bucket_name).list()
            for folder in expected_folders:
                if any(f.get('name') == folder for f in files):
                    folders_found += 1

            if folders_found > 0:
                print(f"    [✓] Folder structure exists ({folders_found} folders)")
                checks_passed += 1
            else:
                print(f"    [✗] No folder structure found")

        except Exception as e:
            print(f"    [✗] Error checking folders: {e}")

        # Check 4: Test upload/download
        checks_total += 1
        try:
            test_path = 'raw/pending/.test'
            test_content = b'test'

            # Upload
            self.client.storage.from_(self.bucket_name).upload(
                path=test_path,
                file=test_content,
                file_options={'upsert': 'true'}
            )

            # Download
            downloaded = self.client.storage.from_(self.bucket_name).download(test_path)

            # Delete
            self.client.storage.from_(self.bucket_name).remove([test_path])

            print(f"    [✓] Upload/download/delete works")
            checks_passed += 1

        except Exception as e:
            print(f"    [✗] Upload/download/delete failed: {e}")

        # Summary
        print(f"\n[*] Verification Summary:")
        print(f"    Checks passed: {checks_passed}/{checks_total}")

        if checks_passed == checks_total:
            print(f"    [+] All checks passed! ✓")
            return True
        else:
            print(f"    [-] Some checks failed")
            return False

    def run_setup(self, verify_only: bool = False) -> bool:
        """
        Run complete setup process.

        Args:
            verify_only: If True, only verify without creating

        Returns:
            bool: True if setup successful
        """
        print("=" * 60)
        print("SUPABASE STORAGE SETUP")
        print("=" * 60)

        # Step 1: Connect
        if not self.connect():
            return False

        if verify_only:
            # Only verify
            return self.verify_setup()

        # Step 2: Check if bucket exists
        exists = self.bucket_exists()

        # Step 3: Create bucket if needed
        if not exists:
            if not self.create_bucket():
                return False
        else:
            print(f"[*] Skipping bucket creation (already exists)")

        # Step 4: Create folder structure
        if not self.create_folder_structure():
            print(f"[!] Warning: Folder structure creation had issues")
            print(f"    Folders will be created automatically when files are uploaded")

        # Step 5: Verify setup
        if not self.verify_setup():
            print(f"\n[-] Setup verification failed")
            return False

        print("\n" + "=" * 60)
        print("SETUP COMPLETE ✓")
        print("=" * 60)
        print(f"\nNext steps:")
        print(f"  1. Run SQL schema (copy from ../README.md to Supabase SQL Editor)")
        print(f"  2. Upload documents:")
        print(f"     python scripts/upload_documents.py --dir /path/to/docs")
        print(f"  3. Process documents:")
        print(f"     python process_documents_storage.py")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Setup Supabase Storage for RAG system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full setup (create bucket + verify)
  python setup_storage.py

  # Only verify existing setup
  python setup_storage.py --verify-only

  # Use custom bucket name
  python setup_storage.py --bucket-name my-custom-bucket

  # Show what would be done (dry run)
  python setup_storage.py --dry-run
        """
    )

    parser.add_argument(
        '--bucket-name',
        type=str,
        default=None,
        help='Bucket name (default: from .env or "vehicle-documents")'
    )

    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify setup, do not create anything'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    # Get configuration from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    bucket_name = args.bucket_name or os.getenv('SUPABASE_STORAGE_BUCKET', 'vehicle-documents')

    # Validate configuration
    if not supabase_url or not supabase_key:
        print("[-] ERROR: Missing configuration")
        print("    Please set in .env file:")
        print("      SUPABASE_URL=https://your-project.supabase.co")
        print("      SUPABASE_SERVICE_ROLE_KEY=eyJ...")
        print("\n    Or see .env.storage.example for full configuration")
        sys.exit(1)

    # Dry run mode
    if args.dry_run:
        print("=" * 60)
        print("DRY RUN MODE")
        print("=" * 60)
        print(f"\nWould perform the following:")
        print(f"  1. Connect to: {supabase_url}")
        print(f"  2. Create bucket: '{bucket_name}'")
        print(f"  3. Settings:")
        print(f"     - Public: No (private)")
        print(f"     - File size limit: 50 MB")
        print(f"     - Allowed types: PDF, DOCX, PPTX")
        print(f"  4. Create folders:")
        print(f"     - raw/pending/")
        print(f"     - raw/processed/")
        print(f"     - raw/failed/")
        print(f"  5. Verify setup")
        print(f"\nRun without --dry-run to actually create")
        sys.exit(0)

    # Run setup
    setup = StorageSetup(supabase_url, supabase_key, bucket_name)

    try:
        success = setup.run_setup(verify_only=args.verify_only)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n[-] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
