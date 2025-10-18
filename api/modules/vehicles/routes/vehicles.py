#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/vehicles/routes/vehicles.py
# CRUD operations for vehicles

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..models.schemas import (
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleResponse,
    VehicleDetailResponse,
    VehicleListResponse,
    VehicleStatistics,
    SuccessResponse,
    ErrorResponse,
)
from ..services.vehicle_service import get_vehicle_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=VehicleListResponse, responses={500: {"model": ErrorResponse}})
async def list_vehicles(
    status: Optional[str] = Query(None, description="Filter by status (active, maintenance, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page")
):
    """
    Get list of all vehicles.
    
    **Features:**
    - Pagination support
    - Filter by status
    - Returns expiry indicators
    
    **Example:**
    ```
    GET /api/vehicles?status=active&page=1&page_size=50
    ```
    
    **Returns:**
    - List of vehicles with metadata
    - Total count
    - Expiry status for each vehicle
    """
    try:
        vehicle_service = get_vehicle_service()
        
        offset = (page - 1) * page_size
        
        vehicles, total = await vehicle_service.get_all(
            status=status,
            limit=page_size,
            offset=offset
        )
        
        # Convert to response models
        vehicle_responses = [
            VehicleResponse(**vehicle) for vehicle in vehicles
        ]
        
        logger.info(f"Retrieved {len(vehicle_responses)} vehicles (page {page}, total: {total})")
        
        return VehicleListResponse(
            vehicles=vehicle_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list vehicles: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve vehicles: {str(e)}"
        )


@router.post("", response_model=VehicleResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def create_vehicle(request: VehicleCreateRequest):
    """
    Create a new vehicle.
    
    **Required:**
    - `registration_number` - Unique VRN
    
    **Optional:**
    - `vin_number` - 17-character VIN (must be unique)
    - `make` - Vehicle manufacturer
    - `model` - Vehicle model
    - `insurance_expiry_date` - Insurance expiry
    - `motor_tax_expiry_date` - Motor tax expiry
    - `nct_expiry_date` - NCT expiry
    - `status` - Vehicle status (default: active)
    - `current_driver_id` - Current driver UUID
    
    **Example:**
    ```json
    {
      "registration_number": "191-D-12345",
      "vin_number": "WF0XXGCDXXB12345",
      "make": "Ford",
      "model": "Focus",
      "insurance_expiry_date": "2025-12-01",
      "motor_tax_expiry_date": "2025-08-31",
      "nct_expiry_date": "2026-05-20",
      "status": "active"
    }
    ```
    
    **Returns:**
    - Created vehicle with UUID
    - Expiry indicators calculated
    """
    try:
        vehicle_service = get_vehicle_service()
        
        # Create vehicle
        vehicle_id = await vehicle_service.create_vehicle(
            registration_number=request.registration_number,
            vin_number=request.vin_number,
            make=request.make,
            model=request.model,
            insurance_expiry_date=request.insurance_expiry_date,
            motor_tax_expiry_date=request.motor_tax_expiry_date,
            nct_expiry_date=request.nct_expiry_date,
            status=request.status.value if request.status else 'active',
            current_driver_id=request.current_driver_id
        )
        
        # Retrieve created vehicle
        vehicle = await vehicle_service.get_by_id(vehicle_id)
        
        if not vehicle:
            raise HTTPException(
                status_code=500,
                detail="Vehicle created but could not be retrieved"
            )
        
        logger.info(f"✅ Created vehicle: {vehicle_id} ({request.registration_number})")
        
        return VehicleResponse(**vehicle)
        
    except ValueError as e:
        # Validation errors (duplicate VRN/VIN)
        logger.warning(f"Validation error creating vehicle: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create vehicle: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create vehicle: {str(e)}"
        )


@router.get("/{vehicle_id}", response_model=VehicleDetailResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_vehicle(vehicle_id: str):
    """
    Get detailed vehicle information with documents.
    
    **Returns:**
    - Complete vehicle details
    - All linked documents
    - Document statistics
    - Expiry indicators
    
    **Example:**
    ```
    GET /api/vehicles/uuid-vehicle-123
    ```
    
    **Use cases:**
    - View vehicle profile
    - Check linked documents
    - Review expiry dates
    """
    try:
        vehicle_service = get_vehicle_service()
        
        # Get vehicle with documents
        result = await vehicle_service.get_with_documents(vehicle_id)
        
        if not result:
            logger.warning(f"Vehicle not found: {vehicle_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle not found: {vehicle_id}"
            )
        
        from ..models.schemas import DocumentRegistryItem
        
        # Convert documents to response models
        documents = [
            DocumentRegistryItem(
                id=str(doc['id']),
                vehicle_id=str(doc['vehicle_id']) if doc.get('vehicle_id') else None,
                raw_file_path=doc.get('raw_file_path'),
                markdown_file_path=doc.get('markdown_file_path'),
                document_type=doc.get('document_type'),
                status=doc['status'],
                extracted_data=doc.get('extracted_data', {}),
                uploaded_at=doc['uploaded_at'],
                updated_at=doc['updated_at'],
                filename=doc.get('raw_file_path', '').split('/')[-1] if doc.get('raw_file_path') else None,
                is_indexed=(doc['status'] == 'processed')
            )
            for doc in result['documents']
        ]
        
        return VehicleDetailResponse(
            vehicle=VehicleResponse(**result['vehicle']),
            documents=documents,
            total_documents=len(documents),
            unassigned_documents=sum(1 for d in documents if d.status.value == 'unassigned'),
            pending_documents=sum(1 for d in documents if d.status.value in ['pending_ocr', 'pending_indexing'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get vehicle {vehicle_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve vehicle: {str(e)}"
        )


@router.put("/{vehicle_id}", response_model=VehicleResponse, responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def update_vehicle(vehicle_id: str, request: VehicleUpdateRequest):
    """
    Update vehicle information.
    
    **All fields are optional** - only provided fields will be updated.
    
    **Example:**
    ```json
    {
      "insurance_expiry_date": "2026-01-01",
      "status": "maintenance"
    }
    ```
    
    **Use cases:**
    - Update expiry dates
    - Change vehicle status
    - Update make/model
    - Assign driver
    """
    try:
        vehicle_service = get_vehicle_service()
        
        # Check if vehicle exists
        existing = await vehicle_service.get_by_id(vehicle_id)
        if not existing:
            logger.warning(f"Vehicle not found for update: {vehicle_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle not found: {vehicle_id}"
            )
        
        # Update vehicle
        success = await vehicle_service.update(
            vehicle_id=vehicle_id,
            registration_number=request.registration_number,
            vin_number=request.vin_number,
            make=request.make,
            model=request.model,
            insurance_expiry_date=request.insurance_expiry_date,
            motor_tax_expiry_date=request.motor_tax_expiry_date,
            nct_expiry_date=request.nct_expiry_date,
            status=request.status.value if request.status else None,
            current_driver_id=request.current_driver_id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update vehicle"
            )
        
        # Retrieve updated vehicle
        updated_vehicle = await vehicle_service.get_by_id(vehicle_id)
        
        logger.info(f"✅ Updated vehicle: {vehicle_id}")
        
        return VehicleResponse(**updated_vehicle)
        
    except ValueError as e:
        # Validation errors (duplicate VRN/VIN)
        logger.warning(f"Validation error updating vehicle: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update vehicle {vehicle_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update vehicle: {str(e)}"
        )


@router.delete("/{vehicle_id}", response_model=SuccessResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def delete_vehicle(vehicle_id: str):
    """
    Delete vehicle from system.
    
    **⚠️ WARNING:** This permanently deletes the vehicle!
    
    **What happens:**
    - Vehicle record deleted
    - Documents are UNLINKED (vehicle_id set to NULL)
    - Documents remain in system but become unassigned
    - Chunks in vector database remain intact
    
    **Cannot be undone.**
    
    **Example:**
    ```
    DELETE /api/vehicles/uuid-vehicle-123
    ```
    """
    try:
        vehicle_service = get_vehicle_service()
        
        # Check if vehicle exists
        existing = await vehicle_service.get_by_id(vehicle_id)
        if not existing:
            logger.warning(f"Vehicle not found for deletion: {vehicle_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle not found: {vehicle_id}"
            )
        
        # Delete vehicle
        success = await vehicle_service.delete(vehicle_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete vehicle"
            )
        
        vrn = existing.get('registration_number', vehicle_id)
        logger.info(f"🗑️ Deleted vehicle: {vehicle_id} ({vrn})")
        
        return SuccessResponse(
            success=True,
            message=f"Vehicle '{vrn}' deleted successfully. Associated documents have been unlinked."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete vehicle {vehicle_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete vehicle: {str(e)}"
        )


@router.get("/stats/overview", response_model=VehicleStatistics, responses={500: {"model": ErrorResponse}})
async def get_vehicle_statistics():
    """
    Get comprehensive vehicle fleet statistics.
    
    **Returns:**
    - Total vehicles by status
    - Expiry warnings (within 30 days)
    - Expired documents count
    
    **Statistics include:**
    - `total_vehicles` - Total fleet size
    - `active_vehicles` - Currently active
    - `maintenance_vehicles` - Under maintenance
    - `inactive_vehicles` - Inactive/parked
    - `insurance_expiring_soon` - Expiring within 30 days
    - `motor_tax_expiring_soon` - Expiring within 30 days
    - `nct_expiring_soon` - Expiring within 30 days
    - `insurance_expired` - Already expired
    - `motor_tax_expired` - Already expired
    - `nct_expired` - Already expired
    
    **Use cases:**
    - Fleet management dashboard
    - Compliance monitoring
    - Renewal planning
    """
    try:
        vehicle_service = get_vehicle_service()
        
        stats = await vehicle_service.get_statistics()
        
        return VehicleStatistics(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get vehicle statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )