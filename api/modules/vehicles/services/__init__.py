# ============================================================================
# api/modules/vehicles/services/__init__.py
# ============================================================================
# Vehicle services initialization and exports

from .vehicle_service import VehicleService, get_vehicle_service
from .document_registry_service import DocumentRegistryService, get_document_registry_service

__all__ = [
    # Vehicle Service
    "VehicleService",
    "get_vehicle_service",
    
    # Document Registry Service
    "DocumentRegistryService",
    "get_document_registry_service",
]