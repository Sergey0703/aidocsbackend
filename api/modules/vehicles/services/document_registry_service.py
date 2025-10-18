#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/vehicles/services/document_registry_service.py
# Service for managing document_registry table

import logging
import sys
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional, Any
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


class DocumentRegistryService:
    """Service for managing document_registry operations"""
    
    def __init__(self):
        self._config = None
        logger.info("✅ DocumentRegistryService initialized")
    
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
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_registry_entry(
        self,
        raw_file_path: str,
        status: str = 'pending_indexing',
        vehicle_id: Optional[str] = None,
        document_type: Optional[str] = None,
        markdown_file_path: Optional[str] = None,
        extracted_data: Optional[Dict] = None
    ) -> str:
        """
        Create new document registry entry
        
        Args:
            raw_file_path: Path to raw file (required)
            status: Document status (default: 'pending_indexing')
            vehicle_id: Optional vehicle UUID
            document_type: Optional document type
            markdown_file_path: Optional path to markdown file
            extracted_data: Optional extracted data (VRN, dates, etc.)
        
        Returns:
            str: UUID of created registry entry
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            registry_id = str(uuid.uuid4())
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vecs.document_registry (
                        id,
                        vehicle_id,
                        raw_file_path,
                        markdown_file_path,
                        document_type,
                        status,
                        extracted_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    registry_id,
                    vehicle_id,
                    raw_file_path,
                    markdown_file_path,
                    document_type,
                    status,
                    psycopg2.extras.Json(extracted_data or {})
                ))
                
                result = cur.fetchone()
                conn.commit()
            
            conn.close()
            
            logger.info(f"✅ Created registry entry: {registry_id} for {raw_file_path}")
            return result[0] if result else registry_id
            
        except Exception as e:
            logger.error(f"Failed to create registry entry: {e}", exc_info=True)
            raise
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_by_id(self, registry_id: str) -> Optional[Dict[str, Any]]:
        """Get registry entry by ID"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.document_registry
                    WHERE id = %s
                """, (registry_id,))
                
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                return dict(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get registry entry {registry_id}: {e}", exc_info=True)
            return None
    
    async def find_by_raw_path(self, raw_file_path: str) -> Optional[Dict[str, Any]]:
        """Find registry entry by raw file path"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.document_registry
                    WHERE raw_file_path = %s
                """, (raw_file_path,))
                
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                return dict(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find registry by raw path: {e}", exc_info=True)
            return None
    
    async def find_by_markdown_path(self, markdown_file_path: str) -> Optional[Dict[str, Any]]:
        """Find registry entry by markdown file path"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.document_registry
                    WHERE markdown_file_path = %s
                """, (markdown_file_path,))
                
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                return dict(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find registry by markdown path: {e}", exc_info=True)
            return None
    
    async def get_by_vehicle(
        self,
        vehicle_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all documents for a vehicle
        
        Args:
            vehicle_id: Vehicle UUID
            status: Optional status filter
        
        Returns:
            List of registry entries
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return []
            
            query = """
                SELECT * FROM vecs.document_registry
                WHERE vehicle_id = %s
            """
            params = [vehicle_id]
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY uploaded_at DESC"
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                results = cur.fetchall()
            
            conn.close()
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"Failed to get documents for vehicle {vehicle_id}: {e}", exc_info=True)
            return []
    
    async def get_by_status(self, status: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get documents by status
        
        Args:
            status: Document status ('processed', 'pending_assignment', 'unassigned', 'assigned', etc.)
            limit: Maximum number of results
        
        Returns:
            List of registry entries
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return []
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.document_registry
                    WHERE status = %s
                    ORDER BY uploaded_at DESC
                    LIMIT %s
                """, (status, limit))
                
                results = cur.fetchall()
            
            conn.close()
            
            logger.info(f"📋 Retrieved {len(results)} documents with status='{status}'")
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"Failed to get documents by status: {e}", exc_info=True)
            return []
    
    async def get_unassigned(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get all unassigned documents (not linked to any vehicle)
        
        NOTE: This now returns documents with status='unassigned' specifically
        For documents needing VRN analysis, use get_by_status('processed')
        For documents ready to link, use get_by_status('pending_assignment')
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of unassigned registry entries
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return []
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.document_registry
                    WHERE vehicle_id IS NULL
                    AND status = 'unassigned'
                    ORDER BY uploaded_at DESC
                    LIMIT %s
                """, (limit,))
                
                results = cur.fetchall()
            
            conn.close()
            
            logger.info(f"📋 Retrieved {len(results)} unassigned documents (status='unassigned')")
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error(f"Failed to get unassigned documents: {e}", exc_info=True)
            return []
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update(
        self,
        registry_id: str,
        vehicle_id: Optional[str] = None,
        markdown_file_path: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        extracted_data: Optional[Dict] = None
    ) -> bool:
        """
        Update registry entry
        
        Returns:
            bool: Success status
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return False
            
            updates = []
            params = []
            
            if vehicle_id is not None:
                updates.append("vehicle_id = %s")
                params.append(vehicle_id)
            
            if markdown_file_path is not None:
                updates.append("markdown_file_path = %s")
                params.append(markdown_file_path)
            
            if document_type is not None:
                updates.append("document_type = %s")
                params.append(document_type)
            
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            
            if extracted_data is not None:
                updates.append("extracted_data = extracted_data || %s::jsonb")
                params.append(psycopg2.extras.Json(extracted_data))
            
            if not updates:
                logger.warning(f"No fields to update for registry {registry_id}")
                return True
            
            params.append(registry_id)
            
            query = f"""
                UPDATE vecs.document_registry
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            with conn.cursor() as cur:
                cur.execute(query, params)
                affected = cur.rowcount
                conn.commit()
            
            conn.close()
            
            if affected > 0:
                logger.info(f"✅ Updated registry entry: {registry_id}")
                return True
            else:
                logger.warning(f"Registry entry not found: {registry_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update registry {registry_id}: {e}", exc_info=True)
            return False
    
    async def update_status(self, registry_id: str, status: str) -> bool:
        """Update only status of registry entry"""
        return await self.update(registry_id, status=status)
    
    async def update_registry_by_raw_path(
        self,
        raw_file_path: str,
        markdown_file_path: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """Update registry entry by raw file path"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return False
            
            updates = []
            params = []
            
            if markdown_file_path is not None:
                updates.append("markdown_file_path = %s")
                params.append(markdown_file_path)
            
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            
            if not updates:
                return True
            
            params.append(raw_file_path)
            
            query = f"""
                UPDATE vecs.document_registry
                SET {', '.join(updates)}
                WHERE raw_file_path = %s
            """
            
            with conn.cursor() as cur:
                cur.execute(query, params)
                affected = cur.rowcount
                conn.commit()
            
            conn.close()
            
            if affected > 0:
                logger.info(f"✅ Updated registry by raw path: {raw_file_path}")
                return True
            else:
                logger.warning(f"Registry not found for raw path: {raw_file_path}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update by raw path: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # DELETE
    # ========================================================================
    
    async def delete(self, registry_id: str) -> bool:
        """Delete registry entry (CASCADE deletes chunks)"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM vecs.document_registry
                    WHERE id = %s
                """, (registry_id,))
                
                affected = cur.rowcount
                conn.commit()
            
            conn.close()
            
            if affected > 0:
                logger.info(f"🗑️ Deleted registry entry: {registry_id}")
                return True
            else:
                logger.warning(f"Registry entry not found: {registry_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delete registry {registry_id}: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # VEHICLE LINKING
    # ========================================================================
    
    async def link_to_vehicle(self, registry_id: str, vehicle_id: str) -> bool:
        """Link document to vehicle and set status to 'assigned'"""
        return await self.update(registry_id, vehicle_id=vehicle_id, status='assigned')
    
    async def unlink_from_vehicle(self, registry_id: str) -> bool:
        """Unlink document from vehicle and set status to 'unassigned'"""
        return await self.update(registry_id, vehicle_id=None, status='unassigned')
    
    # ========================================================================
    # ANALYSIS & GROUPING
    # ========================================================================
    
    async def group_by_extracted_vrn(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group documents with status='pending_assignment' by extracted VRN
        
        Returns:
            Dict mapping VRN → list of documents
        """
        try:
            pending_assignment = await self.get_by_status('pending_assignment', limit=1000)
            
            grouped = {}
            
            for doc in pending_assignment:
                extracted_data = doc.get('extracted_data', {})
                vrn = extracted_data.get('vrn')
                
                if vrn:
                    if vrn not in grouped:
                        grouped[vrn] = []
                    grouped[vrn].append(doc)
            
            logger.info(f"📊 Grouped pending_assignment documents by VRN: {len(grouped)} groups found")
            return grouped
            
        except Exception as e:
            logger.error(f"Failed to group by VRN: {e}", exc_info=True)
            return {}
    
    async def get_unassigned_with_grouping(self) -> Dict[str, Any]:
        """
        Get documents organized by status for Document Manager
        
        Returns:
            {
                'processed': [...],      # Documents needing VRN analysis
                'grouped': [             # Documents with VRN (pending_assignment)
                    {
                        'vrn': '191-D-12345',
                        'documents': [...],
                        'vehicleDetails': {...} or None
                    }
                ],
                'unassigned': [...],     # Documents without VRN (manual assignment needed)
                'total_processed': 12,
                'total_grouped': 5,
                'total_unassigned': 3,
                'vehicles_needing_creation': 2,
                'vehicles_with_documents': 3
            }
        """
        try:
            # Get documents by status
            processed = await self.get_by_status('processed', limit=1000)
            pending_assignment = await self.get_by_status('pending_assignment', limit=1000)
            unassigned = await self.get_by_status('unassigned', limit=1000)
            
            logger.info(
                f"📋 Retrieved documents: "
                f"processed={len(processed)}, "
                f"pending_assignment={len(pending_assignment)}, "
                f"unassigned={len(unassigned)}"
            )
            
            # Group pending_assignment documents by VRN
            vrn_groups = {}
            for doc in pending_assignment:
                extracted_data = doc.get('extracted_data', {})
                vrn = extracted_data.get('vrn')
                
                if vrn:
                    if vrn not in vrn_groups:
                        vrn_groups[vrn] = []
                    vrn_groups[vrn].append(doc)
            
            # Format grouped results with vehicle details
            grouped_results = []
            vehicles_needing_creation = 0
            vehicles_with_documents = 0
            
            for vrn, docs in vrn_groups.items():
                # Check if vehicle exists
                vehicle_details = await self._find_vehicle_by_vrn(vrn)
                
                if vehicle_details:
                    vehicles_with_documents += 1
                else:
                    vehicles_needing_creation += 1
                
                grouped_results.append({
                    'vrn': vrn,
                    'documents': docs,
                    'document_count': len(docs),
                    'vehicleDetails': vehicle_details
                })
            
            result = {
                'processed': processed,
                'grouped': grouped_results,
                'unassigned': unassigned,
                'total_processed': len(processed),
                'total_grouped': len(grouped_results),
                'total_unassigned': len(unassigned),
                'vehicles_needing_creation': vehicles_needing_creation,
                'vehicles_with_documents': vehicles_with_documents
            }
            
            logger.info(
                f"📊 Document Manager data: "
                f"processed={len(processed)}, "
                f"grouped={len(grouped_results)} groups, "
                f"unassigned={len(unassigned)}, "
                f"need_creation={vehicles_needing_creation}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get unassigned with grouping: {e}", exc_info=True)
            return {
                'processed': [],
                'grouped': [],
                'unassigned': [],
                'total_processed': 0,
                'total_grouped': 0,
                'total_unassigned': 0,
                'vehicles_needing_creation': 0,
                'vehicles_with_documents': 0
            }
    
    async def _find_vehicle_by_vrn(self, vrn: str) -> Optional[Dict[str, Any]]:
        """Find vehicle by registration number"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        id::text,
                        registration_number,
                        make,
                        model,
                        vin_number,
                        status
                    FROM vecs.vehicles
                    WHERE LOWER(registration_number) = LOWER(%s)
                    LIMIT 1
                """, (vrn,))
                
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                return dict(result)
            
            return None
            
        except Exception as e:
            logger.debug(f"Vehicle not found for VRN {vrn}: {e}")
            return None
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get document registry statistics"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return {}
            
            stats = {}
            
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM vecs.document_registry")
                stats['total_documents'] = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT status, COUNT(*) 
                    FROM vecs.document_registry 
                    GROUP BY status
                """)
                stats['by_status'] = {row[0]: row[1] for row in cur.fetchall()}
                
                cur.execute("""
                    SELECT document_type, COUNT(*) 
                    FROM vecs.document_registry 
                    WHERE document_type IS NOT NULL
                    GROUP BY document_type
                """)
                stats['by_type'] = {row[0]: row[1] for row in cur.fetchall()}
                
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE vehicle_id IS NOT NULL) as assigned,
                        COUNT(*) FILTER (WHERE vehicle_id IS NULL) as unassigned
                    FROM vecs.document_registry
                """)
                row = cur.fetchone()
                stats['assigned'] = row[0]
                stats['unassigned'] = row[1]
            
            conn.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            return {}


# Singleton
_document_registry_service: Optional[DocumentRegistryService] = None

def get_document_registry_service() -> DocumentRegistryService:
    """Get or create document registry service singleton"""
    global _document_registry_service
    
    if _document_registry_service is None:
        _document_registry_service = DocumentRegistryService()
    
    return _document_registry_service