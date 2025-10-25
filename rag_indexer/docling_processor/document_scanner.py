#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document scanner module for Docling
Scans directories for documents to convert OR scans Supabase Storage via database
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class DocumentScanner:
    """Scanner for finding documents to convert"""

    def __init__(self, config, registry_manager=None):
        """
        Initialize document scanner

        Args:
            config: DoclingConfig instance
            registry_manager: Optional DocumentRegistryManager for Storage mode
        """
        self.config = config
        self.registry_manager = registry_manager
        self.scan_stats = {
            'total_files': 0,
            'supported_files': 0,
            'unsupported_files': 0,
            'oversized_files': 0,
            'by_format': {}
        }
    
    def scan_directory(self):
        """
        Scan directory for documents
        
        Returns:
            list: List of file paths to process
        """
        print(f"[*] Scanning directory: {self.config.RAW_DOCUMENTS_DIR}")
        print(f"   Recursive: {'Yes' if self.config.RECURSIVE_SCAN else 'No'}")
        print(f"   Supported formats: {', '.join(self.config.SUPPORTED_FORMATS)}")
        
        files_to_process = []
        
        if self.config.RECURSIVE_SCAN:
            # Recursive scan
            for root, dirs, files in os.walk(self.config.RAW_DOCUMENTS_DIR):
                for file in files:
                    file_path = Path(root) / file
                    self._process_file(file_path, files_to_process)
        else:
            # Non-recursive scan
            input_dir = Path(self.config.RAW_DOCUMENTS_DIR)
            for file_path in input_dir.iterdir():
                if file_path.is_file():
                    self._process_file(file_path, files_to_process)
        
        self._print_scan_summary()
        
        return files_to_process
    
    def _process_file(self, file_path, files_to_process):
        """
        Process a single file during scan
        
        Args:
            file_path: Path to file
            files_to_process: List to append valid files
        """
        self.scan_stats['total_files'] += 1
        
        # Check if format is supported
        if not self.config.is_supported_format(file_path):
            self.scan_stats['unsupported_files'] += 1
            return
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.MAX_FILE_SIZE_MB:
            self.scan_stats['oversized_files'] += 1
            print(f"   [!] Skipping oversized file: {file_path.name} ({file_size_mb:.1f} MB)")
            return
        
        # Count by format
        ext = file_path.suffix.lower().lstrip('.')
        self.scan_stats['by_format'][ext] = self.scan_stats['by_format'].get(ext, 0) + 1
        
        # Add to processing list
        self.scan_stats['supported_files'] += 1
        files_to_process.append(file_path)
    
    def _print_scan_summary(self):
        """Print scan summary"""
        print(f"\n[*] Scan Summary:")
        print(f"   Total files found: {self.scan_stats['total_files']}")
        print(f"   [+] Supported files: {self.scan_stats['supported_files']}")
        print(f"   [-] Unsupported files: {self.scan_stats['unsupported_files']}")
        
        if self.scan_stats['oversized_files'] > 0:
            print(f"   [!] Oversized files (skipped): {self.scan_stats['oversized_files']}")
        
        if self.scan_stats['by_format']:
            print(f"\n   Files by format:")
            for fmt, count in sorted(self.scan_stats['by_format'].items()):
                print(f"      .{fmt}: {count}")
    
    def get_scan_stats(self):
        """Get scan statistics"""
        return self.scan_stats.copy()
    
    def check_already_converted(self, input_path):
        """
        Check if file was already converted
        
        Args:
            input_path: Input file path
        
        Returns:
            bool: True if already converted
        """
        # Generate output path
        output_path = self.config.get_output_path(input_path)
        
        # Check if output exists
        if not output_path.exists():
            return False
        
        # Compare modification times
        input_mtime = input_path.stat().st_mtime
        output_mtime = output_path.stat().st_mtime
        
        # If output is newer than input, already converted
        return output_mtime > input_mtime
    
    def filter_already_converted(self, files_to_process, incremental=True):
        """
        Filter out already converted files
        
        Args:
            files_to_process: List of file paths
            incremental: If True, skip already converted files
        
        Returns:
            list: Filtered list of files
        """
        if not incremental:
            return files_to_process
        
        print(f"\n[*] Checking for already converted files...")
        
        new_files = []
        skipped_count = 0
        
        for file_path in files_to_process:
            if self.check_already_converted(file_path):
                skipped_count += 1
            else:
                new_files.append(file_path)
        
        if skipped_count > 0:
            print(f"    Skipping {skipped_count} already converted files")
            print(f"    {len(new_files)} new/modified files to process")
        else:
            print(f"   All {len(files_to_process)} files need conversion")
        
        return new_files

    # ================================================
    # NEW METHODS FOR SUPABASE STORAGE INTEGRATION
    # ================================================

    def scan_storage(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Scan Supabase Storage for pending documents via database registry.

        This method queries the document_registry table for documents with
        storage_status='pending' instead of scanning the filesystem.

        Args:
            limit: Maximum number of documents to return (None = no limit)

        Returns:
            List[Dict]: List of pending document records with metadata
        """
        if not self.registry_manager:
            raise ValueError(
                "registry_manager must be provided to DocumentScanner for Storage mode"
            )

        print(f"[*] Scanning Supabase Storage for pending documents...")

        try:
            # Query pending documents from database
            pending_docs = self.registry_manager.get_pending_documents(limit=limit)

            # Update scan stats
            self.scan_stats['total_files'] = len(pending_docs)
            self.scan_stats['supported_files'] = len(pending_docs)

            # Count by content type
            for doc in pending_docs:
                content_type = doc.get('content_type', 'unknown')
                ext = self._content_type_to_extension(content_type)
                self.scan_stats['by_format'][ext] = self.scan_stats['by_format'].get(ext, 0) + 1

            self._print_storage_scan_summary(pending_docs)

            return pending_docs

        except Exception as e:
            print(f"[!] Error scanning Storage: {e}")
            return []

    def _print_storage_scan_summary(self, pending_docs: List[Dict]):
        """
        Print summary of Storage scan.

        Args:
            pending_docs: List of pending documents
        """
        print(f"\n[*] Storage Scan Summary:")
        print(f"   Total pending documents: {len(pending_docs)}")

        if pending_docs:
            total_size = sum(doc.get('file_size_bytes', 0) for doc in pending_docs)
            total_size_mb = total_size / (1024 * 1024)
            print(f"   Total size: {total_size_mb:.2f} MB")

            if self.scan_stats['by_format']:
                print(f"\n   Files by format:")
                for fmt, count in sorted(self.scan_stats['by_format'].items()):
                    print(f"      {fmt}: {count}")

            print(f"\n   Sample documents:")
            for doc in pending_docs[:5]:  # Show first 5
                uploaded_at = doc.get('uploaded_at', 'unknown')
                if isinstance(uploaded_at, datetime):
                    uploaded_at = uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f"      - {doc['original_filename']} (uploaded: {uploaded_at})")

            if len(pending_docs) > 5:
                print(f"      ... and {len(pending_docs) - 5} more")

    @staticmethod
    def _content_type_to_extension(content_type: str) -> str:
        """
        Convert MIME content type to file extension.

        Args:
            content_type: MIME type

        Returns:
            str: File extension (without dot)
        """
        type_map = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'application/vnd.ms-powerpoint': 'ppt',
        }
        return type_map.get(content_type, 'unknown')


def create_document_scanner(config, registry_manager=None):
    """
    Create document scanner instance

    Args:
        config: DoclingConfig instance
        registry_manager: Optional DocumentRegistryManager for Storage mode

    Returns:
        DocumentScanner: Scanner instance
    """
    return DocumentScanner(config, registry_manager)