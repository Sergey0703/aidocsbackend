# api/modules/indexing/routes/__init__.py
# Routes package initialization

from .indexing import router as indexing_router
from .documents import router as documents_router
from .conversion import router as conversion_router
from .monitoring import router as monitoring_router

__all__ = [
    "indexing_router",
    "documents_router",
    "conversion_router",
    "monitoring_router",
]