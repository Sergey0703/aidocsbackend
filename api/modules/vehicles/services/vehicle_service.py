#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/vehicles/services/vehicle_service.py
# Service for managing vehicles table

import logging
import sys
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
import uuid

from ..models.schemas import VehicleStatus

logger = logging.getLogger(__name__)


class VehicleService:
    """Service for managing vehicle operations"""
    
    def __init__(self):
        self._config = None
        logger.info("✅ VehicleService initialized")
    
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
    
    def _calculate_expiry_indicators(self, vehicle_data: Dict) -> Dict:
        """Calculate expiry status indicators for a vehicle"""
        today = date.today()
        
        indicators = {
            'is_insurance_expired': False,
            'is_motor_tax_expired': False,
            'is_nct_expired': False,
            'days_until_insurance_expiry': None,
            'days_until_motor_tax_expiry': None,
            'days_until_nct_expiry': None,
        }
        
        # Insurance
        if vehicle_data.get('insurance_expiry_date'):
            expiry = vehicle_data['insurance_expiry_date']
            if isinstance(expiry, str):
                expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
            
            delta = (expiry - today).days
            indicators['days_until_insurance_expiry'] = delta
            indicators['is_insurance_expired'] = delta < 0
        
        # Motor Tax
        if vehicle_data.get('motor_tax_expiry_date'):
            expiry = vehicle_data['motor_tax_expiry_date']
            if isinstance(expiry, str):
                expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
            
            delta = (expiry - today).days
            indicators['days_until_motor_tax_expiry'] = delta
            indicators['is_motor_tax_expired'] = delta < 0
        
        # NCT
        if vehicle_data.get('nct_expiry_date'):
            expiry = vehicle_data['nct_expiry_date']
            if isinstance(expiry, str):
                expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
            
            delta = (expiry - today).days
            indicators['days_until_nct_expiry'] = delta
            indicators['is_nct_expired'] = delta < 0
        
        return indicators
    
    # ========================================================================
    # CREATE
    # ========================================================================
    
    async def create_vehicle(
        self,
        registration_number: str,
        vin_number: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        insurance_expiry_date: Optional[date] = None,
        motor_tax_expiry_date: Optional[date] = None,
        nct_expiry_date: Optional[date] = None,
        status: str = 'active',
        current_driver_id: Optional[str] = None
    ) -> str:
        """
        Create new vehicle
        
        Args:
            registration_number: Vehicle registration number (required)
            vin_number: Vehicle Identification Number
            make: Vehicle manufacturer
            model: Vehicle model
            insurance_expiry_date: Insurance expiry
            motor_tax_expiry_date: Motor tax expiry
            nct_expiry_date: NCT expiry
            status: Vehicle status
            current_driver_id: Current driver UUID
        
        Returns:
            str: UUID of created vehicle
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            vehicle_id = str(uuid.uuid4())
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vecs.vehicles (
                        id,
                        registration_number,
                        vin_number,
                        make,
                        model,
                        insurance_expiry_date,
                        motor_tax_expiry_date,
                        nct_expiry_date,
                        status,
                        current_driver_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    vehicle_id,
                    registration_number,
                    vin_number,
                    make,
                    model,
                    insurance_expiry_date,
                    motor_tax_expiry_date,
                    nct_expiry_date,
                    status,
                    current_driver_id
                ))
                
                result = cur.fetchone()
                conn.commit()
            
            conn.close()
            
            logger.info(f"✅ Created vehicle: {vehicle_id} ({registration_number})")
            return result[0] if result else vehicle_id
            
        except psycopg2.IntegrityError as e:
            logger.error(f"Integrity error creating vehicle: {e}")
            if 'vehicles_registration_number_key' in str(e):
                raise ValueError(f"Vehicle with registration number '{registration_number}' already exists")
            elif 'vehicles_vin_number_key' in str(e):
                raise ValueError(f"Vehicle with VIN '{vin_number}' already exists")
            raise
        except Exception as e:
            logger.error(f"Failed to create vehicle: {e}", exc_info=True)
            raise
    
    # ========================================================================
    # READ
    # ========================================================================
    
    async def get_by_id(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get vehicle by ID"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.vehicles
                    WHERE id = %s
                """, (vehicle_id,))
                
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                vehicle_data = dict(result)
                # Add expiry indicators
                indicators = self._calculate_expiry_indicators(vehicle_data)
                vehicle_data.update(indicators)
                return vehicle_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get vehicle {vehicle_id}: {e}", exc_info=True)
            return None
    
    async def get_by_registration(self, registration_number: str) -> Optional[Dict[str, Any]]:
        """Get vehicle by registration number"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM vecs.vehicles
                    WHERE registration_number = %s
                """, (registration_number,))
                
                result = cur.fetchone()
            
            conn.close()
            
            if result:
                vehicle_data = dict(result)
                indicators = self._calculate_expiry_indicators(vehicle_data)
                vehicle_data.update(indicators)
                return vehicle_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get vehicle by registration: {e}", exc_info=True)
            return None
    
    async def get_all(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get all vehicles with pagination
        
        Args:
            status: Optional status filter
            limit: Maximum results
            offset: Offset for pagination
        
        Returns:
            Tuple of (vehicles list, total count)
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return [], 0
            
            # Build query
            query = "SELECT * FROM vecs.vehicles"
            count_query = "SELECT COUNT(*) FROM vecs.vehicles"
            params = []
            
            if status:
                query += " WHERE status = %s"
                count_query += " WHERE status = %s"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Get total count
                cur.execute(count_query, params if status else [])
                result = cur.fetchone()
                total = result['count'] if result else 0
                
                # Get vehicles
                cur.execute(query, params + [limit, offset])
                results = cur.fetchall()
            
            conn.close()
            
            vehicles = []
            for result in results:
                vehicle_data = dict(result)
                indicators = self._calculate_expiry_indicators(vehicle_data)
                vehicle_data.update(indicators)
                vehicles.append(vehicle_data)
            
            logger.info(f"Retrieved {len(vehicles)} vehicles (total: {total})")
            return vehicles, total
            
        except Exception as e:
            logger.error(f"Failed to get vehicles: {e}", exc_info=True)
            return [], 0
    
    async def get_with_documents(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vehicle with its documents
        
        Returns:
            Dict with 'vehicle' and 'documents' keys
        """
        try:
            # Get vehicle
            vehicle = await self.get_by_id(vehicle_id)
            if not vehicle:
                return None
            
            # Get documents
            from .document_registry_service import get_document_registry_service
            registry_service = get_document_registry_service()
            
            documents = await registry_service.get_by_vehicle(vehicle_id)
            
            return {
                'vehicle': vehicle,
                'documents': documents,
                'total_documents': len(documents)
            }
            
        except Exception as e:
            logger.error(f"Failed to get vehicle with documents: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # UPDATE
    # ========================================================================
    
    async def update(
        self,
        vehicle_id: str,
        registration_number: Optional[str] = None,
        vin_number: Optional[str] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        insurance_expiry_date: Optional[date] = None,
        motor_tax_expiry_date: Optional[date] = None,
        nct_expiry_date: Optional[date] = None,
        status: Optional[str] = None,
        current_driver_id: Optional[str] = None
    ) -> bool:
        """
        Update vehicle information
        
        Returns:
            bool: Success status
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return False
            
            updates = []
            params = []
            
            if registration_number is not None:
                updates.append("registration_number = %s")
                params.append(registration_number)
            
            if vin_number is not None:
                updates.append("vin_number = %s")
                params.append(vin_number)
            
            if make is not None:
                updates.append("make = %s")
                params.append(make)
            
            if model is not None:
                updates.append("model = %s")
                params.append(model)
            
            if insurance_expiry_date is not None:
                updates.append("insurance_expiry_date = %s")
                params.append(insurance_expiry_date)
            
            if motor_tax_expiry_date is not None:
                updates.append("motor_tax_expiry_date = %s")
                params.append(motor_tax_expiry_date)
            
            if nct_expiry_date is not None:
                updates.append("nct_expiry_date = %s")
                params.append(nct_expiry_date)
            
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            
            if current_driver_id is not None:
                updates.append("current_driver_id = %s")
                params.append(current_driver_id)
            
            if not updates:
                logger.warning(f"No fields to update for vehicle {vehicle_id}")
                return True
            
            params.append(vehicle_id)
            
            query = f"""
                UPDATE vecs.vehicles
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            with conn.cursor() as cur:
                cur.execute(query, params)
                affected = cur.rowcount
                conn.commit()
            
            conn.close()
            
            if affected > 0:
                logger.info(f"✅ Updated vehicle: {vehicle_id}")
                return True
            else:
                logger.warning(f"Vehicle not found: {vehicle_id}")
                return False
            
        except psycopg2.IntegrityError as e:
            logger.error(f"Integrity error updating vehicle: {e}")
            if 'vehicles_registration_number_key' in str(e):
                raise ValueError(f"Registration number '{registration_number}' already exists")
            elif 'vehicles_vin_number_key' in str(e):
                raise ValueError(f"VIN '{vin_number}' already exists")
            raise
        except Exception as e:
            logger.error(f"Failed to update vehicle {vehicle_id}: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # DELETE
    # ========================================================================
    
    async def delete(self, vehicle_id: str) -> bool:
        """
        Delete vehicle
        
        Note: Documents will be unlinked (vehicle_id set to NULL)
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                return False
            
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM vecs.vehicles
                    WHERE id = %s
                """, (vehicle_id,))
                
                affected = cur.rowcount
                conn.commit()
            
            conn.close()
            
            if affected > 0:
                logger.info(f"🗑️ Deleted vehicle: {vehicle_id}")
                return True
            else:
                logger.warning(f"Vehicle not found: {vehicle_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delete vehicle {vehicle_id}: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get vehicle fleet statistics"""
        try:
            conn = self._get_db_connection()
            if not conn:
                return {}
            
            stats = {}
            today = date.today()
            warning_days = 30  # Days before expiry to warn
            
            with conn.cursor() as cur:
                # Total vehicles
                cur.execute("SELECT COUNT(*) FROM vecs.vehicles")
                stats['total_vehicles'] = cur.fetchone()[0]
                
                # By status
                cur.execute("""
                    SELECT status, COUNT(*) 
                    FROM vecs.vehicles 
                    GROUP BY status
                """)
                for row in cur.fetchall():
                    stats[f'{row[0]}_vehicles'] = row[1]
                
                # Expiring soon (within 30 days)
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (
                            WHERE insurance_expiry_date BETWEEN %s AND %s
                        ) as insurance_expiring,
                        COUNT(*) FILTER (
                            WHERE motor_tax_expiry_date BETWEEN %s AND %s
                        ) as motor_tax_expiring,
                        COUNT(*) FILTER (
                            WHERE nct_expiry_date BETWEEN %s AND %s
                        ) as nct_expiring
                    FROM vecs.vehicles
                """, (
                    today, today + timedelta(days=warning_days),
                    today, today + timedelta(days=warning_days),
                    today, today + timedelta(days=warning_days)
                ))
                row = cur.fetchone()
                stats['insurance_expiring_soon'] = row[0]
                stats['motor_tax_expiring_soon'] = row[1]
                stats['nct_expiring_soon'] = row[2]
                
                # Expired
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE insurance_expiry_date < %s) as insurance_expired,
                        COUNT(*) FILTER (WHERE motor_tax_expiry_date < %s) as motor_tax_expired,
                        COUNT(*) FILTER (WHERE nct_expiry_date < %s) as nct_expired
                    FROM vecs.vehicles
                """, (today, today, today))
                row = cur.fetchone()
                stats['insurance_expired'] = row[0]
                stats['motor_tax_expired'] = row[1]
                stats['nct_expired'] = row[2]
            
            conn.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            return {}


# Singleton
_vehicle_service: Optional[VehicleService] = None

def get_vehicle_service() -> VehicleService:
    """Get or create vehicle service singleton"""
    global _vehicle_service
    
    if _vehicle_service is None:
        _vehicle_service = VehicleService()
    
    return _vehicle_service