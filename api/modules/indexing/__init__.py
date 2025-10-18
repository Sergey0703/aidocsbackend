# api/modules/indexing/__init__.py
# Indexing module initialization and exports

from .routes.indexing import router as indexing_router
from .routes.documents import router as documents_router
from .routes.conversion import router as conversion_router
from .routes.monitoring import router as monitoring_router

# Module metadata
__module_name__ = "indexing"
__module_version__ = "1.0.0"
__module_description__ = "Document indexing and conversion"

# Export all routers
__all__ = [
    "indexing_router",
    "documents_router",
    "conversion_router",
    "monitoring_router",
]