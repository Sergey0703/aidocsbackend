"""
Supabase Storage Manager for document uploads and downloads.

This module provides an abstraction layer for interacting with Supabase Storage,
handling file uploads, downloads, moves, and deletions.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import BinaryIO, Optional, Union
from datetime import datetime, timedelta

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SupabaseStorageManager:
    """
    Manages document storage operations with Supabase Storage.

    Handles:
    - Uploading documents to Storage
    - Downloading documents to temporary locations
    - Moving documents between folders (pending → processed/failed)
    - Deleting documents
    - Listing documents in specific prefixes
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        temp_dir: Optional[str] = None
    ):
        """
        Initialize Supabase Storage Manager.

        Args:
            supabase_url: Supabase project URL (from env if not provided)
            supabase_key: Supabase service role key (from env if not provided)
            bucket_name: Storage bucket name (from env if not provided)
            temp_dir: Temporary directory for downloads (from env if not provided)
        """
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.bucket_name = bucket_name or os.getenv('SUPABASE_STORAGE_BUCKET', 'vehicle-documents')
        self.temp_dir = temp_dir or os.getenv('STORAGE_TEMP_DIR', '/tmp/rag_storage_temp')

        # Validate required settings
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment or passed to constructor"
            )

        # Initialize Supabase client
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

        # Create temp directory if it doesn't exist
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized SupabaseStorageManager with bucket '{self.bucket_name}'")

    def upload_document(
        self,
        file: Union[BinaryIO, bytes, str],
        original_filename: str,
        document_type: Optional[str] = None,
        target_folder: str = 'raw/pending'
    ) -> dict:
        """
        Upload a document to Supabase Storage.

        Args:
            file: File content (BinaryIO, bytes, or file path)
            original_filename: Original name of the file
            document_type: Type of document (insurance, nct, etc.) - unused for now
            target_folder: Target folder in bucket (default: raw/pending)

        Returns:
            dict: {
                'storage_path': str,
                'original_filename': str,
                'file_size': int,
                'content_type': str,
                'uploaded_at': str (ISO format)
            }

        Raises:
            Exception: If upload fails
        """
        try:
            # Read file content
            if isinstance(file, str):
                # File path provided
                with open(file, 'rb') as f:
                    file_content = f.read()
                file_size = os.path.getsize(file)
            elif isinstance(file, bytes):
                file_content = file
                file_size = len(file)
            else:
                # BinaryIO
                file_content = file.read()
                file_size = len(file_content)

            # Use original filename with timestamp prefix to avoid conflicts
            import time
            timestamp = int(time.time())
            safe_filename = original_filename.replace(' ', '_')  # Replace spaces
            unique_filename = f"{timestamp}_{safe_filename}"

            # Build storage path
            storage_path = f"{target_folder}/{unique_filename}"

            # Detect content type
            content_type = self._get_content_type(original_filename)

            # Upload to Supabase Storage
            logger.info(f"Uploading {original_filename} to {storage_path}")

            response = self.client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "x-upsert": "false"  # Don't overwrite existing files
                }
            )

            logger.info(f"Successfully uploaded {original_filename} ({file_size} bytes)")

            return {
                'storage_path': storage_path,
                'original_filename': original_filename,
                'file_size': file_size,
                'content_type': content_type,
                'uploaded_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to upload {original_filename}: {e}")
            raise

    def download_to_temp(self, storage_path: str) -> str:
        """
        Download a document from Storage to temporary directory.

        Args:
            storage_path: Path in Storage bucket (e.g., 'raw/pending/uuid_file.pdf')

        Returns:
            str: Local temporary file path

        Raises:
            Exception: If download fails
        """
        try:
            logger.info(f"Downloading {storage_path} from Storage")

            # Download file content
            response = self.client.storage.from_(self.bucket_name).download(storage_path)

            # Generate local temp path
            filename = Path(storage_path).name
            temp_path = os.path.join(self.temp_dir, filename)

            # Write to temp file
            with open(temp_path, 'wb') as f:
                f.write(response)

            logger.info(f"Downloaded to {temp_path} ({len(response)} bytes)")

            return temp_path

        except Exception as e:
            logger.error(f"Failed to download {storage_path}: {e}")
            raise

    def move_document(self, old_path: str, new_folder: str) -> str:
        """
        Move a document to a new folder within the Storage bucket.

        This is useful for moving documents from pending → processed/failed.

        Args:
            old_path: Current path in bucket (e.g., 'raw/pending/file.pdf')
            new_folder: Destination folder (e.g., 'raw/processed')

        Returns:
            str: New full path of the moved file

        Raises:
            Exception: If move fails
        """
        try:
            # Extract filename from old path
            from pathlib import Path
            filename = Path(old_path).name

            # Build complete destination path with filename
            new_path = f"{new_folder}/{filename}"

            logger.info(f"Moving {old_path} → {new_path}")

            # Supabase Storage doesn't have native move, so we copy + delete
            response = self.client.storage.from_(self.bucket_name).move(
                from_path=old_path,
                to_path=new_path
            )

            logger.info(f"Successfully moved document to {new_path}")
            return new_path

        except Exception as e:
            logger.error(f"Failed to move {old_path} → {new_folder}/{filename}: {e}")
            raise

    def delete_document(self, storage_path: str) -> bool:
        """
        Delete a document from Storage.

        Args:
            storage_path: Path in bucket to delete

        Returns:
            bool: True if successful

        Raises:
            Exception: If deletion fails
        """
        try:
            logger.info(f"Deleting {storage_path}")

            response = self.client.storage.from_(self.bucket_name).remove([storage_path])

            logger.info(f"Successfully deleted document")
            return True

        except Exception as e:
            logger.error(f"Failed to delete {storage_path}: {e}")
            raise

    def list_documents(self, prefix: str = '', limit: int = 1000) -> list[dict]:
        """
        List documents in a specific folder.

        Args:
            prefix: Folder prefix (e.g., 'raw/pending/')
            limit: Maximum number of results

        Returns:
            list[dict]: List of file metadata dicts
        """
        try:
            logger.info(f"Listing documents with prefix '{prefix}'")

            response = self.client.storage.from_(self.bucket_name).list(
                path=prefix,
                options={'limit': limit}
            )

            logger.info(f"Found {len(response)} documents")

            return response

        except Exception as e:
            logger.error(f"Failed to list documents with prefix '{prefix}': {e}")
            raise

    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Generate a temporary signed URL for downloading a file.

        Args:
            storage_path: Path in bucket
            expires_in: Expiration time in seconds (default: 1 hour)

        Returns:
            str: Signed URL

        Raises:
            Exception: If URL generation fails
        """
        try:
            logger.info(f"Generating signed URL for {storage_path} (expires in {expires_in}s)")

            response = self.client.storage.from_(self.bucket_name).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )

            signed_url = response.get('signedURL')

            logger.info(f"Generated signed URL")

            return signed_url

        except Exception as e:
            logger.error(f"Failed to generate signed URL for {storage_path}: {e}")
            raise

    def file_exists(self, storage_path: str) -> bool:
        """
        Check if a file exists in Storage.

        Args:
            storage_path: Path in bucket

        Returns:
            bool: True if file exists
        """
        try:
            # Try to get file info
            folder = str(Path(storage_path).parent)
            filename = Path(storage_path).name

            files = self.list_documents(prefix=folder)

            return any(f.get('name') == filename for f in files)

        except Exception as e:
            logger.error(f"Error checking existence of {storage_path}: {e}")
            return False

    def cleanup_temp_file(self, temp_path: str) -> bool:
        """
        Delete a temporary file.

        Args:
            temp_path: Local temp file path

        Returns:
            bool: True if deleted successfully
        """
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"Cleaned up temp file: {temp_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup temp file {temp_path}: {e}")
            return False

    @staticmethod
    def _get_content_type(filename: str) -> str:
        """
        Determine content type from filename extension.

        Args:
            filename: Name of the file

        Returns:
            str: MIME type
        """
        extension = Path(filename).suffix.lower()

        content_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json'
        }

        return content_types.get(extension, 'application/octet-stream')


# Convenience function for getting a shared instance
_storage_manager_instance: Optional[SupabaseStorageManager] = None

def get_storage_manager() -> SupabaseStorageManager:
    """
    Get or create a shared SupabaseStorageManager instance.

    Returns:
        SupabaseStorageManager: Shared instance
    """
    global _storage_manager_instance

    if _storage_manager_instance is None:
        _storage_manager_instance = SupabaseStorageManager()

    return _storage_manager_instance
