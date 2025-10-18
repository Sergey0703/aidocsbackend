#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/document_inbox/services/__init__.py

from .vrn_extraction_service import (
    VRNExtractionService,
    get_vrn_extraction_service
)

__all__ = [
    'VRNExtractionService',
    'get_vrn_extraction_service'
]