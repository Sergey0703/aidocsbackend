# api/modules/document_inbox/utils/__init__.py
# Document Inbox utilities initialization

from .vrn_patterns import (
    VRNPatterns,
    extract_vrn,
    extract_all_vrns,
    normalize_vrn,
    is_vrn_format
)

__all__ = [
    'VRNPatterns',
    'extract_vrn',
    'extract_all_vrns',
    'normalize_vrn',
    'is_vrn_format'
]