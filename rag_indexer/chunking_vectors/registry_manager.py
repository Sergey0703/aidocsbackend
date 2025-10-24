# rag_indexer/chunking_vectors/registry_manager.py
# ЗАМЕНИТЬ ПОЛНОСТЬЮ этот файл

import logging
import psycopg2
import psycopg2.extras
from typing import Optional, Dict, List
from uuid import UUID
import uuid
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentRegistryManager:
    """
    Manages document registry for tracking processed files
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        logger.info("[+] Document Registry Manager initialized")
    
    def get_or_create_registry_entry(
        self, 
        file_path: str,
        file_hash: Optional[str] = None
    ) -> Optional[str]:
        """
        Get existing or create new registry entry for a document
        
        Args:
            file_path: Path to markdown file
            file_hash: Optional file hash
            
        Returns:
            registry_id (UUID) or None if failed
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()
            
            # 🆕 SEARCH BY MARKDOWN_FILE_PATH (not file_path!)
            cur.execute("""
                SELECT id FROM vecs.document_registry 
                WHERE markdown_file_path = %s
            """, (file_path,))
            
            result = cur.fetchone()
            
            if result:
                registry_id = str(result[0])
                logger.debug(f"Found existing registry entry: {registry_id} for {file_path}")
                cur.close()
                conn.close()
                return registry_id
            
            # 🆕 CREATE NEW ENTRY IF NOT FOUND
            # Since this is called during markdown loading, we only have markdown path
            import uuid
            registry_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO vecs.document_registry (
                    id,
                    markdown_file_path,
                    status,
                    extracted_data
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                registry_id,
                file_path,
                'pending_indexing',  # Default status
                psycopg2.extras.Json({})
            ))
            
            conn.commit()
            
            logger.info(f"[+] Created new registry entry: {registry_id} for {file_path}")
            
            cur.close()
            conn.close()
            
            return registry_id
            
        except Exception as e:
            logger.error(f"Failed to get/create registry entry for {file_path}: {e}")
            return None
    
    def update_file_hash(self, registry_id: str, file_hash: str) -> bool:
        """
        Update file hash for registry entry

        Args:
            registry_id: Registry UUID
            file_hash: File hash to store

        Returns:
            bool: Success status
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            cur.execute("""
                UPDATE vecs.document_registry
                SET extracted_data = extracted_data || %s::jsonb
                WHERE id = %s
            """, (
                psycopg2.extras.Json({'file_hash': file_hash}),
                registry_id
            ))

            conn.commit()
            cur.close()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Failed to update file hash: {e}")
            return False

    def update_registry_status(self, registry_id: str, status: str) -> bool:
        """
        Update status for registry entry

        Args:
            registry_id: Registry UUID
            status: New status (e.g. 'processed', 'indexed', 'failed')

        Returns:
            bool: Success status
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            cur.execute("""
                UPDATE vecs.document_registry
                SET status = %s, updated_at = now()
                WHERE id = %s
            """, (status, registry_id))

            conn.commit()
            rows_updated = cur.rowcount
            cur.close()
            conn.close()

            if rows_updated > 0:
                logger.debug(f"[+] Updated registry {registry_id} status to '{status}'")
                return True
            else:
                logger.warning(f"[!] No registry found with id {registry_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update registry status for {registry_id}: {e}")
            return False

    # ================================================
    # NEW METHODS FOR SUPABASE STORAGE INTEGRATION
    # ================================================

    def create_entry_from_storage(
        self,
        storage_path: str,
        original_filename: str,
        file_size: int,
        content_type: str,
        storage_bucket: str = 'vehicle-documents',
        document_type: Optional[str] = None,
        vehicle_id: Optional[str] = None,
        extracted_data: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Create a new registry entry for a document uploaded to Storage.

        Args:
            storage_path: Path in Storage bucket (e.g., 'raw/pending/uuid_file.pdf')
            original_filename: Original filename
            file_size: File size in bytes
            content_type: MIME type
            storage_bucket: Bucket name (default: 'vehicle-documents')
            document_type: Type of document (insurance, nct, etc.)
            vehicle_id: UUID of vehicle (if known)
            extracted_data: Additional metadata

        Returns:
            str: Registry UUID or None if failed
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            registry_id = str(uuid.uuid4())

            # Prepare extracted_data
            metadata = extracted_data or {}
            metadata['uploaded_filename'] = original_filename

            cur.execute("""
                INSERT INTO vecs.document_registry (
                    id,
                    storage_bucket,
                    storage_path,
                    original_filename,
                    file_size_bytes,
                    content_type,
                    uploaded_at,
                    storage_status,
                    document_type,
                    vehicle_id,
                    status,
                    extracted_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                registry_id,
                storage_bucket,
                storage_path,
                original_filename,
                file_size,
                content_type,
                datetime.utcnow(),
                'pending',  # storage_status
                document_type,
                vehicle_id,
                'pending_processing',  # status (for overall processing)
                psycopg2.extras.Json(metadata)
            ))

            conn.commit()

            logger.info(f"[+] Created registry entry {registry_id} for {original_filename} at {storage_path}")

            cur.close()
            conn.close()

            return registry_id

        except Exception as e:
            logger.error(f"Failed to create registry entry from storage: {e}")
            return None

    def update_storage_status(
        self,
        registry_id: str,
        new_status: str,
        new_storage_path: Optional[str] = None
    ) -> bool:
        """
        Update storage processing status and optionally the storage path.

        Args:
            registry_id: Registry UUID
            new_status: New status (pending, processing, processed, failed, indexed)
            new_storage_path: New storage path (if file was moved)

        Returns:
            bool: Success status
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            if new_storage_path:
                cur.execute("""
                    UPDATE vecs.document_registry
                    SET storage_status = %s,
                        storage_path = %s,
                        updated_at = now()
                    WHERE id = %s
                """, (new_status, new_storage_path, registry_id))
            else:
                cur.execute("""
                    UPDATE vecs.document_registry
                    SET storage_status = %s,
                        updated_at = now()
                    WHERE id = %s
                """, (new_status, registry_id))

            conn.commit()
            rows_updated = cur.rowcount

            cur.close()
            conn.close()

            if rows_updated > 0:
                logger.info(f"[+] Updated storage_status to '{new_status}' for {registry_id}")
                return True
            else:
                logger.warning(f"[!] No registry found with id {registry_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update storage status: {e}")
            return False

    def update_markdown_path(self, registry_id: str, markdown_path: str) -> bool:
        """
        Update the markdown file path for a registry entry.

        This is called after conversion (Docling) completes.

        Args:
            registry_id: Registry UUID
            markdown_path: Path to generated markdown file

        Returns:
            bool: Success status
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()

            cur.execute("""
                UPDATE vecs.document_registry
                SET markdown_file_path = %s,
                    updated_at = now()
                WHERE id = %s
            """, (markdown_path, registry_id))

            conn.commit()
            rows_updated = cur.rowcount

            cur.close()
            conn.close()

            if rows_updated > 0:
                logger.info(f"[+] Updated markdown_file_path for {registry_id}")
                return True
            else:
                logger.warning(f"[!] No registry found with id {registry_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update markdown path: {e}")
            return False

    def get_pending_documents(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all documents with storage_status='pending' (waiting for processing).

        Args:
            limit: Maximum number of results (None = no limit)

        Returns:
            List[Dict]: List of pending document records
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = """
                SELECT
                    id,
                    storage_bucket,
                    storage_path,
                    original_filename,
                    file_size_bytes,
                    content_type,
                    uploaded_at,
                    storage_status,
                    document_type,
                    vehicle_id,
                    extracted_data
                FROM vecs.document_registry
                WHERE storage_status = 'pending'
                  AND storage_path IS NOT NULL
                  AND original_filename IS NOT NULL
                ORDER BY uploaded_at ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            cur.execute(query)
            results = cur.fetchall()

            # Convert UUID to string
            documents = []
            for row in results:
                doc = dict(row)
                doc['id'] = str(doc['id'])
                if doc.get('vehicle_id'):
                    doc['vehicle_id'] = str(doc['vehicle_id'])
                documents.append(doc)

            logger.info(f"[+] Found {len(documents)} pending documents")

            cur.close()
            conn.close()

            return documents

        except Exception as e:
            logger.error(f"Failed to get pending documents: {e}")
            return []

    def get_document_by_storage_path(self, storage_path: str) -> Optional[Dict]:
        """
        Get document registry entry by storage path.

        Args:
            storage_path: Path in Storage bucket

        Returns:
            Dict or None: Document record
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cur.execute("""
                SELECT
                    id,
                    storage_bucket,
                    storage_path,
                    original_filename,
                    file_size_bytes,
                    content_type,
                    uploaded_at,
                    storage_status,
                    markdown_file_path,
                    document_type,
                    vehicle_id,
                    status,
                    extracted_data
                FROM vecs.document_registry
                WHERE storage_path = %s
            """, (storage_path,))

            result = cur.fetchone()

            cur.close()
            conn.close()

            if result:
                doc = dict(result)
                doc['id'] = str(doc['id'])
                if doc.get('vehicle_id'):
                    doc['vehicle_id'] = str(doc['vehicle_id'])
                return doc

            return None

        except Exception as e:
            logger.error(f"Failed to get document by storage path: {e}")
            return None


def create_registry_manager(connection_string: str) -> DocumentRegistryManager:
    """Factory function to create registry manager"""
    return DocumentRegistryManager(connection_string)