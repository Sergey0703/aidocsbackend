#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/services/document_service.py
# Complete implementation with database integration and document management methods

import logging
import sys
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from ..models.schemas import (
    DocumentListItem,
    DocumentInfo,
    DocumentChunk,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing document operations with full database integration"""
    
    def __init__(self):
        self._db_manager = None
        self._config = None
        
        logger.info("✅ DocumentService initialized")
    
    def _setup_backend_path(self):
        """Add rag_indexer to Python path"""
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent
            backend_path = project_root / "rag_indexer"
            
            if backend_path.exists() and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
                logger.debug(f"Added backend path: {backend_path}")
        except Exception as e:
            logger.error(f"Failed to setup backend path: {e}")

    def _get_config(self):
        """Lazy initialization of configuration"""
        if self._config is None:
            self._setup_backend_path()
            from chunking_vectors.config import get_config
            self._config = get_config()
        return self._config

    def _get_db_connection(self):
        """Get a new database connection"""
        try:
            config = self._get_config()
            return psycopg2.connect(config.CONNECTION_STRING)
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}", exc_info=True)
            return None

    def _get_db_manager(self):
        """Lazy initialization of database manager"""
        if self._db_manager is None:
            self._setup_backend_path()
            try:
                from chunking_vectors.database_manager import create_database_manager
                config = self._get_config()
                self._db_manager = create_database_manager(
                    config.CONNECTION_STRING,
                    config.TABLE_NAME
                )
                logger.info("✅ Database manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database manager: {e}", exc_info=True)
                raise
        return self._db_manager

    async def find_records_by_document_id(self, document_id: str) -> List[Dict]:
        """
        Finds all records in the database corresponding to a unique Document ID.
        Searches by registry_id first (if looks like UUID), then falls back to original_path.
        Returns a list of metadata for these records.
        """
        records = []
        try:
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn:
                return []

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 🆕 FIXED: Try searching by registry_id first (if UUID format)
                # Check if document_id looks like a UUID (contains dashes and is 36 chars)
                is_uuid = len(document_id) == 36 and document_id.count('-') == 4

                if is_uuid:
                    # Search by registry_id
                    query = f"""
                        SELECT metadata FROM vecs.{config.TABLE_NAME}
                        WHERE metadata->>'registry_id' = %s
                    """
                    cur.execute(query, (document_id,))
                    results = cur.fetchall()

                    if results:
                        for row in results:
                            records.append(row['metadata'])
                        conn.close()
                        return records

                # Fallback: search by original_path (backward compatibility)
                query = f"""
                    SELECT metadata FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'original_path' = %s
                """
                cur.execute(query, (document_id,))
                results = cur.fetchall()
                for row in results:
                    records.append(row['metadata'])
            conn.close()
            return records
        except Exception as e:
            logger.error(f"Failed to find records for document_id '{document_id}': {e}", exc_info=True)
            return []

    async def delete_records_by_document_id(self, document_id: str) -> int:
        """
        Deletes ALL records from the database corresponding to a Document ID.
        Searches by registry_id first (if looks like UUID), then falls back to original_path.
        Returns the number of deleted records.
        """
        deleted_count = 0
        try:
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn:
                return 0

            with conn.cursor() as cur:
                # 🆕 FIXED: Try deleting by registry_id first (if UUID format)
                is_uuid = len(document_id) == 36 and document_id.count('-') == 4

                if is_uuid:
                    # Delete by registry_id
                    query = f"""
                        DELETE FROM vecs.{config.TABLE_NAME}
                        WHERE metadata->>'registry_id' = %s
                    """
                    cur.execute(query, (document_id,))
                    deleted_count = cur.rowcount

                    if deleted_count > 0:
                        conn.commit()
                        conn.close()
                        logger.info(f"🗑️ Deleted {deleted_count} old chunks for registry_id: {document_id}")
                        return deleted_count

                # Fallback: delete by original_path (backward compatibility)
                query = f"""
                    DELETE FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'original_path' = %s
                """
                cur.execute(query, (document_id,))
                deleted_count = cur.rowcount
                conn.commit()

            conn.close()
            if deleted_count > 0:
                logger.info(f"🗑️ Deleted {deleted_count} old chunks for document ID: {document_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete records for document_id '{document_id}': {e}", exc_info=True)
            return 0

    async def get_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "indexed_at",
        order: str = "desc"
    ) -> tuple[List[DocumentListItem], int, int, int]:
        """
        Get list of documents from database
        """
        try:
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn: return [], 0, 0, 0

            documents = []
            total_documents = 0
            total_chunks = 0
            total_characters = 0

            with conn.cursor() as cur:
                valid_sort_columns = {
                    'indexed_at': "MAX(metadata->>'indexed_at')",
                    'file_name': "metadata->>'file_name'",
                    'total_chunks': "COUNT(*)",
                    'total_characters': "SUM(LENGTH(metadata->>'text'))"
                }
                sort_column = valid_sort_columns.get(sort_by, valid_sort_columns['indexed_at'])
                order_direction = 'DESC' if order.lower() == 'desc' else 'ASC'
                
                query = f"""
                    SELECT 
                        metadata->>'file_name' as filename,
                        COUNT(*) as total_chunks,
                        SUM(LENGTH(metadata->>'text')) as total_characters,
                        MAX(metadata->>'indexed_at') as indexed_at,
                        metadata->>'file_type' as file_type
                    FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'file_name' IS NOT NULL
                    GROUP BY metadata->>'file_name', metadata->>'file_type'
                    ORDER BY {sort_column} {order_direction}
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, (limit, offset))
                rows = cur.fetchall()
                
                for row in rows:
                    filename, chunks, chars, indexed_at_str, file_type = row
                    documents.append(DocumentListItem(
                        filename=filename, total_chunks=chunks, total_characters=chars or 0,
                        indexed_at=datetime.fromisoformat(indexed_at_str) if indexed_at_str else None,
                        file_type=file_type or "md",
                    ))
                
                cur.execute(f"SELECT COUNT(DISTINCT metadata->>'file_name') FROM vecs.{config.TABLE_NAME} WHERE metadata->>'file_name' IS NOT NULL")
                total_documents = (cur.fetchone() or [0])[0]

                cur.execute(f"SELECT COUNT(*), SUM(LENGTH(metadata->>'text')) FROM vecs.{config.TABLE_NAME}")
                total_chunks, total_characters = (cur.fetchone() or (0, 0))

            conn.close()
            
            logger.info(f"Retrieved {len(documents)} documents (total: {total_documents})")
            return documents, total_documents or 0, total_chunks or 0, total_characters or 0
            
        except Exception as e:
            logger.error(f"Failed to get documents: {e}", exc_info=True)
            return [], 0, 0, 0
    
    async def get_document_by_filename(
        self,
        filename: str,
        include_chunks: bool = False
    ) -> Optional[tuple[DocumentInfo, Optional[List[DocumentChunk]]]]:
        """
        Get document details by filename
        """
        try:
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn: return None

            document = None
            chunks = None

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        metadata->>'file_name' as filename,
                        metadata->>'file_path' as file_path,
                        metadata->>'file_type' as file_type,
                        COUNT(*) as total_chunks,
                        SUM(LENGTH(metadata->>'text')) as total_characters,
                        AVG(LENGTH(metadata->>'text')) as avg_chunk_length,
                        MAX(metadata->>'indexed_at') as indexed_at,
                        (array_agg(metadata))[1] as first_metadata
                    FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'file_name' = %s
                    GROUP BY metadata->>'file_name', metadata->>'file_path', metadata->>'file_type'
                """, (filename,))
                
                row = cur.fetchone()
                if not row:
                    conn.close()
                    return None
                
                cur.execute(f"""
                    SELECT (metadata->>'chunk_index')::int
                    FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'file_name' = %s AND metadata->>'chunk_index' IS NOT NULL
                    ORDER BY (metadata->>'chunk_index')::int
                """, (filename,))
                chunk_indices = [r[0] for r in cur.fetchall() if r[0] is not None]
                
                document = DocumentInfo(
                    filename=row['filename'], file_path=row['file_path'], file_type=row['file_type'] or "md",
                    total_chunks=row['total_chunks'], chunk_indices=chunk_indices, total_characters=row['total_characters'] or 0,
                    avg_chunk_length=float(row['avg_chunk_length']) if row['avg_chunk_length'] else 0.0,
                    indexed_at=datetime.fromisoformat(row['indexed_at']) if row['indexed_at'] else None,
                    metadata=row['first_metadata'] or {}
                )
                
                if include_chunks:
                    cur.execute(f"""
                        SELECT 
                            COALESCE((metadata->>'chunk_index')::int, 0) as chunk_index,
                            metadata->>'text' as content,
                            metadata
                        FROM vecs.{config.TABLE_NAME}
                        WHERE metadata->>'file_name' = %s
                        ORDER BY COALESCE((metadata->>'chunk_index')::int, 0)
                    """, (filename,))
                    
                    chunks = [DocumentChunk(
                        chunk_index=r['chunk_index'], content=r['content'] or "",
                        content_length=len(r['content'] or ""), metadata=r['metadata'] or {},
                    ) for r in cur.fetchall()]
                    logger.info(f"Retrieved {len(chunks)} chunks for {filename}")

            conn.close()
            return document, chunks
            
        except Exception as e:
            logger.error(f"Failed to get document {filename}: {e}", exc_info=True)
            return None

    async def get_document_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive document statistics
        """
        try:
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn: raise Exception("No DB connection")

            stats = {}
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT 
                        COUNT(DISTINCT metadata->>'file_name'),
                        COUNT(*),
                        SUM(LENGTH(metadata->>'text'))
                    FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'file_name' IS NOT NULL
                """)
                total_docs, total_chunks, total_chars = cur.fetchone()
                stats.update({
                    "total_documents": total_docs or 0, "total_chunks": total_chunks or 0, "total_characters": total_chars or 0
                })
                
                if total_docs and total_docs > 0:
                    cur.execute(f"""
                        SELECT AVG(c), MIN(c), MAX(c)
                        FROM (SELECT COUNT(*) as c FROM vecs.{config.TABLE_NAME} WHERE metadata->>'file_name' IS NOT NULL GROUP BY metadata->>'file_name') as s
                    """)
                    avg_chunks, min_chunks, max_chunks = cur.fetchone()
                    stats.update({
                        "avg_chunks_per_document": float(avg_chunks) if avg_chunks else 0.0,
                        "min_chunks": min_chunks or 0, "max_chunks": max_chunks or 0
                    })
                else:
                    stats.update({"avg_chunks_per_document": 0.0, "min_chunks": 0, "max_chunks": 0})

                cur.execute(f"""
                    SELECT COALESCE(metadata->>'file_type', 'unknown'), COUNT(DISTINCT metadata->>'file_name')
                    FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'file_name' IS NOT NULL GROUP BY 1
                """)
                stats["file_types"] = {r[0]: r[1] for r in cur.fetchall()}
                
                cur.execute(f"""
                    SELECT CASE 
                        WHEN t.tc < 1000 THEN 'small' WHEN t.tc < 5000 THEN 'medium'
                        WHEN t.tc < 20000 THEN 'large' ELSE 'very_large'
                    END, COUNT(*)
                    FROM (SELECT SUM(LENGTH(metadata->>'text')) as tc FROM vecs.{config.TABLE_NAME} WHERE metadata->>'file_name' IS NOT NULL GROUP BY metadata->>'file_name') as t
                    GROUP BY 1
                """)
                size_dist = {"small": 0, "medium": 0, "large": 0, "very_large": 0}
                for r in cur.fetchall(): size_dist[r[0]] = r[1]
                stats["size_distribution"] = size_dist

            conn.close()
            logger.info(f"Retrieved stats: {stats['total_documents']} documents, {stats['total_chunks']} chunks")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get document stats: {e}", exc_info=True)
            return {
                "total_documents": 0, "total_chunks": 0, "total_characters": 0,
                "avg_chunks_per_document": 0.0, "min_chunks": 0, "max_chunks": 0,
                "file_types": {}, "size_distribution": {"small": 0, "medium": 0, "large": 0, "very_large": 0}
            }

    async def delete_document(self, filename: str, delete_chunks: bool = True) -> tuple[bool, int]:
        """
        Delete document from database
        """
        try:
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn: return False, 0
            
            success = False
            chunks_deleted = 0
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM vecs.{config.TABLE_NAME} WHERE metadata->>'file_name' = %s", (filename,))
                if (cur.fetchone() or [0])[0] > 0:
                    if delete_chunks:
                        cur.execute(f"DELETE FROM vecs.{config.TABLE_NAME} WHERE metadata->>'file_name' = %s", (filename,))
                        chunks_deleted = cur.rowcount
                        conn.commit()
                        logger.info(f"Deleted document {filename}: {chunks_deleted} chunks removed")
                    success = True
                else:
                    logger.warning(f"Document not found for deletion: {filename}")
            conn.close()
            return success, chunks_deleted
        except Exception as e:
            logger.error(f"Failed to delete document {filename}: {e}", exc_info=True)
            return False, 0

    async def get_document_chunks(
        self,
        filename: str,
        limit: int = 100,
        offset: int = 0
    ) -> Optional[tuple[DocumentInfo, List[DocumentChunk]]]:
        """
        Get chunks for a specific document with pagination
        """
        try:
            result = await self.get_document_by_filename(filename, include_chunks=False)
            if result is None: return None
            document_info, _ = result
            
            config = self._get_config()
            conn = self._get_db_connection()
            if not conn: return None, []

            chunks = []
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        COALESCE((metadata->>'chunk_index')::int, 0) as chunk_index,
                        metadata->>'text' as content,
                        metadata
                    FROM vecs.{config.TABLE_NAME}
                    WHERE metadata->>'file_name' = %s
                    ORDER BY COALESCE((metadata->>'chunk_index')::int, 0)
                    LIMIT %s OFFSET %s
                """, (filename, limit, offset))
                
                for row in cur.fetchall():
                    chunks.append(DocumentChunk(
                        chunk_index=row['chunk_index'], content=row['content'] or "",
                        content_length=len(row['content'] or ""), metadata=row['metadata'] or {}
                    ))
            conn.close()
            logger.info(f"Retrieved {len(chunks)} chunks for {filename} (offset: {offset})")
            return document_info, chunks
        except Exception as e:
            logger.error(f"Failed to get chunks for {filename}: {e}", exc_info=True)
            return None, []
            
# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get or create document service singleton"""
    global _document_service
    
    if _document_service is None:
        _document_service = DocumentService()
    
    return _document_service