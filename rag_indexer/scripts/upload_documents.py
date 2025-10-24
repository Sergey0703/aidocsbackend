"""
Upload Documents to Supabase Storage

This script uploads raw documents from a local directory to Supabase Storage
and creates corresponding registry entries in the database.

Usage:
    python upload_documents.py --dir /path/to/documents
    python upload_documents.py --file /path/to/single/document.pdf
    python upload_documents.py --dir /path/to/documents --document-type insurance
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.storage_manager import SupabaseStorageManager
from chunking_vectors.registry_manager import DocumentRegistryManager
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


class DocumentUploader:
    """Upload documents to Supabase Storage and create registry entries."""

    SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.pptx', '.doc', '.ppt']

    def __init__(self):
        """Initialize uploader with Storage Manager and Registry Manager."""
        connection_string = os.getenv('SUPABASE_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("SUPABASE_CONNECTION_STRING not set in environment")

        self.storage_manager = SupabaseStorageManager()
        self.registry_manager = DocumentRegistryManager(connection_string)

        logger.info("DocumentUploader initialized")

    def upload_file(
        self,
        file_path: str,
        document_type: Optional[str] = None,
        vehicle_id: Optional[str] = None
    ) -> bool:
        """
        Upload a single file to Storage and create registry entry.

        Args:
            file_path: Path to the file
            document_type: Type of document (insurance, nct, etc.)
            vehicle_id: UUID of vehicle (if known)

        Returns:
            bool: Success status
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                logger.warning(f"Skipping unsupported file type: {file_path}")
                return False

            logger.info(f"Uploading {file_path.name}...")

            # Upload to Storage
            upload_result = self.storage_manager.upload_document(
                file=str(file_path),
                original_filename=file_path.name,
                document_type=document_type,
                target_folder='raw/pending'
            )

            # Create registry entry
            registry_id = self.registry_manager.create_entry_from_storage(
                storage_path=upload_result['storage_path'],
                original_filename=upload_result['original_filename'],
                file_size=upload_result['file_size'],
                content_type=upload_result['content_type'],
                document_type=document_type,
                vehicle_id=vehicle_id
            )

            if registry_id:
                logger.info(f"✓ Successfully uploaded {file_path.name} (registry_id: {registry_id})")
                return True
            else:
                logger.error(f"✗ Failed to create registry entry for {file_path.name}")
                return False

        except Exception as e:
            logger.error(f"✗ Failed to upload {file_path}: {e}")
            return False

    def upload_directory(
        self,
        directory: str,
        document_type: Optional[str] = None,
        vehicle_id: Optional[str] = None,
        recursive: bool = False
    ) -> tuple[int, int]:
        """
        Upload all supported files from a directory.

        Args:
            directory: Path to directory
            document_type: Type of document for all files
            vehicle_id: UUID of vehicle (if known)
            recursive: Recursively scan subdirectories

        Returns:
            tuple: (success_count, fail_count)
        """
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            logger.error(f"Directory not found: {directory}")
            return (0, 0)

        # Get files
        if recursive:
            files = [
                f for f in directory.rglob('*')
                if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ]
        else:
            files = [
                f for f in directory.iterdir()
                if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ]

        if not files:
            logger.warning(f"No supported files found in {directory}")
            return (0, 0)

        logger.info(f"Found {len(files)} files to upload")

        success_count = 0
        fail_count = 0

        for file_path in files:
            if self.upload_file(str(file_path), document_type, vehicle_id):
                success_count += 1
            else:
                fail_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"Upload Summary:")
        logger.info(f"  Total files:     {len(files)}")
        logger.info(f"  ✓ Successful:    {success_count}")
        logger.info(f"  ✗ Failed:        {fail_count}")
        logger.info(f"{'='*60}\n")

        return (success_count, fail_count)

    def list_pending_uploads(self) -> List[dict]:
        """
        List all documents pending processing in the database.

        Returns:
            List[dict]: Pending documents
        """
        return self.registry_manager.get_pending_documents()


def main():
    """Main entry point for upload script."""
    parser = argparse.ArgumentParser(
        description='Upload documents to Supabase Storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload entire directory
  python upload_documents.py --dir /path/to/documents

  # Upload single file
  python upload_documents.py --file /path/to/insurance.pdf --document-type insurance

  # Upload with vehicle assignment
  python upload_documents.py --dir /path/to/docs --vehicle-id a1b2c3d4-...

  # Recursively upload subdirectories
  python upload_documents.py --dir /path/to/docs --recursive

  # List pending uploads
  python upload_documents.py --list-pending
        """
    )

    parser.add_argument(
        '--dir',
        type=str,
        help='Directory containing documents to upload'
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Single file to upload'
    )

    parser.add_argument(
        '--document-type',
        type=str,
        choices=['insurance', 'nct', 'tax', 'service_record', 'registration', 'other'],
        help='Type of document'
    )

    parser.add_argument(
        '--vehicle-id',
        type=str,
        help='UUID of vehicle to assign document to'
    )

    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Recursively scan subdirectories (only with --dir)'
    )

    parser.add_argument(
        '--list-pending',
        action='store_true',
        help='List all pending uploads in database'
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.dir, args.file, args.list_pending]):
        parser.error("Must specify --dir, --file, or --list-pending")

    if args.file and args.dir:
        parser.error("Cannot specify both --file and --dir")

    if args.recursive and not args.dir:
        parser.error("--recursive only works with --dir")

    # Initialize uploader
    try:
        uploader = DocumentUploader()
    except Exception as e:
        logger.error(f"Failed to initialize uploader: {e}")
        sys.exit(1)

    # Execute requested action
    if args.list_pending:
        pending = uploader.list_pending_uploads()
        if pending:
            logger.info(f"\nFound {len(pending)} pending documents:")
            for doc in pending:
                logger.info(f"  - {doc['original_filename']} (uploaded: {doc['uploaded_at']})")
        else:
            logger.info("No pending documents found")

    elif args.file:
        success = uploader.upload_file(
            args.file,
            document_type=args.document_type,
            vehicle_id=args.vehicle_id
        )
        sys.exit(0 if success else 1)

    elif args.dir:
        success_count, fail_count = uploader.upload_directory(
            args.dir,
            document_type=args.document_type,
            vehicle_id=args.vehicle_id,
            recursive=args.recursive
        )
        sys.exit(0 if fail_count == 0 else 1)


if __name__ == '__main__':
    main()
