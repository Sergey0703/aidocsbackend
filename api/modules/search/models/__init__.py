# api/modules/search/models/__init__.py
# Simplified search module models initialization

from .schemas import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    ErrorResponse
)

__all__ = [
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "ErrorResponse",
]