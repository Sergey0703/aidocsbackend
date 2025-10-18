#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docling Processor Module - Document to Markdown Conversion
Converts raw documents (PDF, DOCX, etc.) to markdown format using Docling library
"""

__version__ = "1.0.0"

from .config_docling import DoclingConfig, get_docling_config
from .document_scanner import DocumentScanner, create_document_scanner
from .document_converter import DocumentConverter, create_document_converter
from .metadata_extractor import MetadataExtractor

__all__ = [
    'DoclingConfig',
    'get_docling_config',
    'DocumentScanner',
    'create_document_scanner',
    'DocumentConverter',
    'create_document_converter',
    'MetadataExtractor',
]