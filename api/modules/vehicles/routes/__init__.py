# ============================================================================
# api/modules/vehicles/routes/__init__.py
# ============================================================================
# Vehicle routes initialization and exports

from .vehicles import router as vehicles_router
from .documents import router as documents_router

__all__ = [
    "vehicles_router",
    "documents_router",
]