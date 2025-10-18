# ============================================================================
# api/modules/document_inbox/__init__.py
# ============================================================================
# Document Inbox module initialization and exports

from .routes import inbox_router

# Module metadata
__module_name__ = "document_inbox"
__module_version__ = "1.0.0"
__module_description__ = "Document inbox management with smart grouping and batch operations"

# Export routers for registration in main.py
__all__ = [
    "inbox_router",
]