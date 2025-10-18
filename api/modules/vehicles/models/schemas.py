#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/vehicles/models/schemas.py
# Pydantic models for Vehicle Management API

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class VehicleStatus(str, Enum):
    """Vehicle status"""
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"
    SOLD = "sold"
    ARCHIVED = "archived"


class DocumentRegistryStatus(str, Enum):
    """Document registry status"""
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    PENDING_OCR = "pending_ocr"
    PENDING_INDEXING = "pending_indexing"
    PROCESSED = "processed"
    ARCHIVED = "archived"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Document type"""
    INSURANCE = "insurance"
    MOTOR_TAX = "motor_tax"
    NCT_CERTIFICATE = "nct_certificate"
    SERVICE_RECORD = "service_record"
    PURCHASE_AGREEMENT = "purchase_agreement"
    REGISTRATION_DOCUMENT = "registration_document"
    DRIVERS_MANUAL = "drivers_manual"
    OTHER = "other"


# ============================================================================
# REQUEST MODELS - VEHICLES
# ============================================================================

class VehicleCreateRequest(BaseModel):
    """Request to create a new vehicle"""
    registration_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Vehicle registration number (VRN)"
    )
    vin_number: Optional[str] = Field(
        default=None,
        max_length=17,
        description="Vehicle Identification Number (VIN)"
    )
    make: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Vehicle manufacturer"
    )
    model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Vehicle model"
    )
    insurance_expiry_date: Optional[date] = None
    motor_tax_expiry_date: Optional[date] = None
    nct_expiry_date: Optional[date] = None
    status: Optional[VehicleStatus] = VehicleStatus.ACTIVE
    current_driver_id: Optional[str] = None
    
    @validator('registration_number')
    def validate_registration_number(cls, v):
        if not v or not v.strip():
            raise ValueError("Registration number cannot be empty")
        return v.strip().upper()
    
    @validator('vin_number')
    def validate_vin_number(cls, v):
        if v:
            v = v.strip().upper()
            if len(v) != 17:
                raise ValueError("VIN must be exactly 17 characters")
        return v


class VehicleUpdateRequest(BaseModel):
    """Request to update vehicle information"""
    registration_number: Optional[str] = None
    vin_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    insurance_expiry_date: Optional[date] = None
    motor_tax_expiry_date: Optional[date] = None
    nct_expiry_date: Optional[date] = None
    status: Optional[VehicleStatus] = None
    current_driver_id: Optional[str] = None
    
    @validator('vin_number')
    def validate_vin_number(cls, v):
        if v:
            v = v.strip().upper()
            if len(v) != 17:
                raise ValueError("VIN must be exactly 17 characters")
        return v


# ============================================================================
# REQUEST MODELS - DOCUMENT LINKING
# ============================================================================

class LinkDocumentRequest(BaseModel):
    """Request to link document to vehicle"""
    registry_id: str = Field(..., description="UUID of document registry entry")


class UnlinkDocumentRequest(BaseModel):
    """Request to unlink document from vehicle"""
    registry_id: str = Field(..., description="UUID of document registry entry")


# ============================================================================
# RESPONSE MODELS - DOCUMENT REGISTRY
# ============================================================================

class DocumentRegistryItem(BaseModel):
    """Document registry entry"""
    id: str
    vehicle_id: Optional[str] = None
    raw_file_path: Optional[str] = None
    markdown_file_path: Optional[str] = None
    document_type: Optional[DocumentType] = None
    status: DocumentRegistryStatus
    extracted_data: Dict[str, Any] = {}
    uploaded_at: datetime
    updated_at: datetime
    
    # Computed fields
    filename: Optional[str] = None
    is_indexed: bool = False
    
    class Config:
        from_attributes = True


# ============================================================================
# RESPONSE MODELS - VEHICLES
# ============================================================================

class VehicleResponse(BaseModel):
    """Basic vehicle information"""
    id: str
    registration_number: str
    vin_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    status: VehicleStatus
    insurance_expiry_date: Optional[date] = None
    motor_tax_expiry_date: Optional[date] = None
    nct_expiry_date: Optional[date] = None
    current_driver_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Status indicators
    is_insurance_expired: bool = False
    is_motor_tax_expired: bool = False
    is_nct_expired: bool = False
    days_until_insurance_expiry: Optional[int] = None
    days_until_motor_tax_expiry: Optional[int] = None
    days_until_nct_expiry: Optional[int] = None
    
    class Config:
        from_attributes = True


class VehicleDetailResponse(BaseModel):
    """Detailed vehicle information with documents"""
    vehicle: VehicleResponse
    documents: List[DocumentRegistryItem] = []
    total_documents: int = 0
    unassigned_documents: int = 0
    pending_documents: int = 0
    
    class Config:
        from_attributes = True


class VehicleListResponse(BaseModel):
    """Response with list of vehicles"""
    vehicles: List[VehicleResponse]
    total: int
    page: int = 1
    page_size: int = 100
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# RESPONSE MODELS - DOCUMENT MANAGEMENT
# ============================================================================

class UnassignedDocumentsResponse(BaseModel):
    """Response with unassigned documents"""
    documents: List[DocumentRegistryItem]
    total: int
    timestamp: datetime = Field(default_factory=datetime.now)


class GroupedDocumentsByVRN(BaseModel):
    """Documents grouped by extracted VRN"""
    vrn: str
    vehicle_exists: bool
    vehicle_details: Optional[VehicleResponse] = None
    suggested_make: Optional[str] = None
    suggested_model: Optional[str] = None
    documents: List[DocumentRegistryItem] = []


class AnalyzeDocumentsResponse(BaseModel):
    """Response with document analysis"""
    grouped: List[GroupedDocumentsByVRN] = []
    unassigned: List[DocumentRegistryItem] = []
    total_grouped: int = 0
    total_unassigned: int = 0
    vehicles_with_documents: int = 0
    vehicles_needing_creation: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class LinkDocumentResponse(BaseModel):
    """Response after linking document"""
    success: bool
    message: str
    document_id: str
    vehicle_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class UnlinkDocumentResponse(BaseModel):
    """Response after unlinking document"""
    success: bool
    message: str
    document_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# RESPONSE MODELS - GENERIC
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    error_type: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "Validation error"
    validation_errors: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# STATISTICS MODELS
# ============================================================================

class VehicleStatistics(BaseModel):
    """Vehicle fleet statistics"""
    total_vehicles: int = 0
    active_vehicles: int = 0
    maintenance_vehicles: int = 0
    inactive_vehicles: int = 0
    insurance_expiring_soon: int = 0
    motor_tax_expiring_soon: int = 0
    nct_expiring_soon: int = 0
    insurance_expired: int = 0
    motor_tax_expired: int = 0
    nct_expired: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class DocumentStatistics(BaseModel):
    """Document registry statistics"""
    total_documents: int = 0
    assigned_documents: int = 0
    unassigned_documents: int = 0
    pending_indexing: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    documents_by_type: Dict[str, int] = {}
    timestamp: datetime = Field(default_factory=datetime.now)