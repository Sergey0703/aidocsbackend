# rag_indexer/chunking_vectors/registry_manager.py
# ЗАМЕНИТЬ ПОЛНОСТЬЮ этот файл

import logging
import psycopg2
from typing import Optional
import hashlib

logger = logging.getLogger(__name__)


class DocumentRegistryManager:
    """
    Manages document registry for tracking processed files
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        logger.info("✅ Document Registry Manager initialized")
    
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
            
            logger.info(f"✅ Created new registry entry: {registry_id} for {file_path}")
            
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


def create_registry_manager(connection_string: str) -> DocumentRegistryManager:
    """Factory function to create registry manager"""
    return DocumentRegistryManager(connection_string)