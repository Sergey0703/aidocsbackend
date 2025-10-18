# api/modules/search/routes/__init__.py
# Search module routes initialization
# Exports routers for registration in main app

from .search import router as search_router
from .system import router as system_router

__all__ = [
    "search_router",
    "system_router",
]