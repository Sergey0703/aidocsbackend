# ============================================================================
# api/modules/vehicles/__init__.py
# ============================================================================
# Vehicle module initialization and exports

from .routes import vehicles_router, documents_router

# Module metadata
__module_name__ = "vehicles"
__module_version__ = "1.0.0"
__module_description__ = "Vehicle fleet management and document linking"

# Export routers for registration in main.py
__all__ = [
    "vehicles_router",
    "documents_router",
]
