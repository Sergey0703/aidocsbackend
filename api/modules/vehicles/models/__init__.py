# ============================================================================
# api/modules/vehicles/models/__init__.py
# ============================================================================
# Vehicle models initialization and exports

from .schemas import (
    # Enums
    VehicleStatus,
    DocumentRegistryStatus,
    DocumentType,
    
    # Request Models - Vehicles
    VehicleCreateRequest,
    VehicleUpdateRequest,
    
    # Request Models - Document Linking
    LinkDocumentRequest,
    UnlinkDocumentRequest,
    
    # Response Models - Document Registry
    DocumentRegistryItem,
    
    # Response Models - Vehicles
    VehicleResponse,
    VehicleDetailResponse,
    VehicleListResponse,
    
    # Response Models - Document Management
    UnassignedDocumentsResponse,
    GroupedDocumentsByVRN,
    AnalyzeDocumentsResponse,
    LinkDocumentResponse,
    UnlinkDocumentResponse,
    
    # Response Models - Generic
    SuccessResponse,
    ErrorResponse,
    ValidationErrorResponse,
    
    # Statistics Models
    VehicleStatistics,
    DocumentStatistics,
)

__all__ = [
    # Enums
    "VehicleStatus",
    "DocumentRegistryStatus",
    "DocumentType",
    
    # Request Models - Vehicles
    "VehicleCreateRequest",
    "VehicleUpdateRequest",
    
    # Request Models - Document Linking
    "LinkDocumentRequest",
    "UnlinkDocumentRequest",
    
    # Response Models - Document Registry
    "DocumentRegistryItem",
    
    # Response Models - Vehicles
    "VehicleResponse",
    "VehicleDetailResponse",
    "VehicleListResponse",
    
    # Response Models - Document Management
    "UnassignedDocumentsResponse",
    "GroupedDocumentsByVRN",
    "AnalyzeDocumentsResponse",
    "LinkDocumentResponse",
    "UnlinkDocumentResponse",
    
    # Response Models - Generic
    "SuccessResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    
    # Statistics Models
    "VehicleStatistics",
    "DocumentStatistics",
]
