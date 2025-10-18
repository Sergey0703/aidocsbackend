# api/modules/search/__init__.py
# Search module initialization

from .routes import search_router, system_router

# Module metadata
__module_name__ = "search"
__module_version__ = "1.0.0"
__module_description__ = "Hybrid search with AI re-ranking"

# Export routers
__all__ = [
    "search_router",
    "system_router",
]