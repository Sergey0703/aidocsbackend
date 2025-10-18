#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/vehicles/routes/documents.py
# Vehicle documents routes

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from api.modules.vehicles.services.vehicle_service import get_vehicle_service
from api.modules.vehicles.services.document_registry_service import get_document_registry_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LinkDocumentRequest(BaseModel):
    """Request to link a document to a vehicle"""
    registry_id: str


class LinkDocumentResponse(BaseModel):
    """Response after linking document"""
    success: bool
    message: str
    vehicle_id: str
    document_id: str


class UnlinkDocumentRequest(BaseModel):
    """Request to unlink a document from a vehicle"""
    registry_id: str


class UnlinkDocumentResponse(BaseModel):
    """Response after unlinking document"""
    success: bool
    message: str
    document_id: str


# ============================================================================
# DOCUMENT LINKING
# ============================================================================

@router.post("/{vehicle_id}/documents/link", response_model=LinkDocumentResponse)
async def link_document_to_vehicle(vehicle_id: str, request: LinkDocumentRequest):
    """
    Link a single document to a vehicle
    """
    try:
        vehicle_service = get_vehicle_service()
        registry_service = get_document_registry_service()
        
        # Validate vehicle exists
        vehicle = await vehicle_service.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle not found: {vehicle_id}"
            )
        
        # Validate document exists
        document = await registry_service.get_by_id(request.registry_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {request.registry_id}"
            )
        
        # Check if already linked to another vehicle
        if document.get('vehicle_id') and document['vehicle_id'] != vehicle_id:
            existing_vehicle = await vehicle_service.get_by_id(document['vehicle_id'])
            existing_vrn = existing_vehicle.get('registration_number', 'another vehicle') if existing_vehicle else 'another vehicle'
            raise HTTPException(
                status_code=400,
                detail=f"Document is already linked to {existing_vrn}"
            )
        
        # Link document
        success = await registry_service.link_to_vehicle(request.registry_id, vehicle_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to link document"
            )
        
        vrn = vehicle.get('registration_number', vehicle_id)
        logger.info(f"✅ Linked document {request.registry_id} to vehicle {vrn}")
        
        return LinkDocumentResponse(
            success=True,
            message=f"Document linked to vehicle {vrn}",
            vehicle_id=vehicle_id,
            document_id=request.registry_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to link document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to link document: {str(e)}"
        )


@router.post("/{vehicle_id}/documents/unlink", response_model=UnlinkDocumentResponse)
async def unlink_document_from_vehicle(vehicle_id: str, request: UnlinkDocumentRequest):
    """
    Unlink a document from a vehicle
    """
    try:
        vehicle_service = get_vehicle_service()
        registry_service = get_document_registry_service()
        
        # Validate vehicle exists
        vehicle = await vehicle_service.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle not found: {vehicle_id}"
            )
        
        # Validate document exists
        document = await registry_service.get_by_id(request.registry_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {request.registry_id}"
            )
        
        # Check if document is actually linked to this vehicle
        if document.get('vehicle_id') != vehicle_id:
            raise HTTPException(
                status_code=400,
                detail="Document is not linked to this vehicle"
            )
        
        # Unlink document
        success = await registry_service.unlink_from_vehicle(request.registry_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to unlink document"
            )
        
        vrn = vehicle.get('registration_number', vehicle_id)
        logger.info(f"✅ Unlinked document {request.registry_id} from vehicle {vrn}")
        
        return UnlinkDocumentResponse(
            success=True,
            message=f"Document unlinked from vehicle {vrn}",
            document_id=request.registry_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlink document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unlink document: {str(e)}"
        )


# ============================================================================
# DOCUMENT QUERIES
# ============================================================================

@router.get("/documents/unassigned")
async def get_unassigned_documents(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Get documents with status='unassigned' (no VRN found, need manual assignment)
    
    NOTE: This returns only documents that have been analyzed and found to have no VRN.
    For documents needing analysis, use /documents/analyze endpoint.
    """
    try:
        registry_service = get_document_registry_service()
        
        documents = await registry_service.get_unassigned(limit=limit)
        
        logger.info(f"📋 Retrieved {len(documents)} unassigned documents")
        
        return {
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Failed to get unassigned documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve unassigned documents: {str(e)}"
        )


@router.get("/documents/analyze")
async def analyze_unassigned_documents():
    """
    Get all documents organized by status for Document Manager
    
    Returns:
        {
            'processed': [...],      # Documents needing VRN analysis (status='processed')
            'grouped': [             # Documents with VRN found (status='pending_assignment')
                {
                    'vrn': '191-D-12345',
                    'documents': [...],
                    'document_count': 2,
                    'vehicleDetails': {...} or None
                }
            ],
            'unassigned': [...],     # Documents without VRN (status='unassigned')
            'total_processed': 12,
            'total_grouped': 5,
            'total_unassigned': 3,
            'vehicles_needing_creation': 2,
            'vehicles_with_documents': 3
        }
    """
    try:
        registry_service = get_document_registry_service()
        
        logger.info("📊 Analyzing documents for Document Manager...")
        
        result = await registry_service.get_unassigned_with_grouping()
        
        logger.info(
            f"✅ Analysis complete: "
            f"processed={result['total_processed']}, "
            f"grouped={result['total_grouped']}, "
            f"unassigned={result['total_unassigned']}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze documents: {str(e)}"
        )


@router.get("/documents/stats")
async def get_document_statistics():
    """
    Get document statistics
    
    Returns statistics about documents by status, type, and assignment state
    """
    try:
        registry_service = get_document_registry_service()
        
        stats = await registry_service.get_statistics()
        
        logger.info(f"📊 Retrieved document statistics")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get document statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.get("/documents/by-status")
async def get_documents_by_status(
    status: str = Query(..., description="Document status to filter by"),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """
    Get documents by specific status
    
    Status values:
    - 'pending_indexing': Uploaded, waiting for indexing
    - 'processed': Indexed, waiting for VRN analysis
    - 'pending_assignment': VRN found, ready to link to vehicle
    - 'unassigned': No VRN found, needs manual assignment
    - 'assigned': Linked to vehicle
    """
    try:
        registry_service = get_document_registry_service()
        
        documents = await registry_service.get_by_status(status, limit=limit)
        
        logger.info(f"📋 Retrieved {len(documents)} documents with status='{status}'")
        
        return {
            "status": status,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Failed to get documents by status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve documents: {str(e)}"
        )