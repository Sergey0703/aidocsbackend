# ============================================================================
# api/modules/document_inbox/routes/__init__.py
# ============================================================================
# Document Inbox routes initialization and exports

from .inbox import router as inbox_router

__all__ = [
    "inbox_router",
]