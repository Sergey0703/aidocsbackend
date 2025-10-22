#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata extractor module for Docling
Extracts and saves metadata from converted documents
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime


class MetadataExtractor:
    """Extractor for document metadata"""
    
    def __init__(self, config):
        """
        Initialize metadata extractor
        
        Args:
            config: DoclingConfig instance
        """
        self.config = config
    
    def extract_metadata(self, input_path, output_path, markdown_content, conversion_time, docling_result=None):
        """
        Extract comprehensive metadata from converted document
        
        Args:
            input_path: Input file path
            output_path: Output markdown file path
            markdown_content: Converted markdown content
            conversion_time: Time taken for conversion
            docling_result: Docling conversion result object
        
        Returns:
            dict: Metadata dictionary
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        # Basic file info
        file_stats = input_path.stat()
        
        metadata = {
            # Original file info
            'original_filename': input_path.name,
            'original_path': str(input_path),
            'original_format': input_path.suffix.lower().lstrip('.'),
            'original_size_bytes': file_stats.st_size,
            'original_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            
            # Output file info
            'markdown_filename': output_path.name,
            'markdown_path': str(output_path),
            'markdown_size_bytes': len(markdown_content.encode('utf-8')),
            
            # Content hash (для определения изменений)
            'content_hash': self._calculate_hash(markdown_content),
            'original_file_hash': self._calculate_file_hash(input_path),
            
            # Conversion info
            'conversion_date': datetime.now().isoformat(),
            'conversion_time_seconds': round(conversion_time, 2),
            'docling_version': self._get_docling_version(),
            
            # Content statistics
            'character_count': len(markdown_content),
            'word_count': len(markdown_content.split()),
            'line_count': markdown_content.count('\n') + 1,
            
            # Quality metrics
            'conversion_quality_score': self._calculate_quality_score(
                input_path, markdown_content, docling_result
            ),
            
            # Document metadata (если доступно)
            'author': self._extract_author(docling_result),
            'creation_date': self._extract_creation_date(docling_result),
            'title': self._extract_title(docling_result),
            
            # Processing settings
            'ocr_enabled': self.config.ENABLE_OCR,
            'tables_extracted': self.config.EXTRACT_TABLES,
        }
        
        return metadata
    
    def _calculate_hash(self, content):
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_docling_version(self):
        """Get Docling version"""
        try:
            import docling
            return docling.__version__
        except:
            return "unknown"
    
    def _calculate_quality_score(self, input_path, markdown_content, docling_result):
        """
        Calculate conversion quality score (0-100)
        
        Args:
            input_path: Input file path
            markdown_content: Converted markdown
            docling_result: Docling result object
        
        Returns:
            float: Quality score
        """
        score = 100.0
        
        # Penalize if content too short
        if len(markdown_content) < 100:
            score -= 30
        elif len(markdown_content) < 500:
            score -= 15
        
        # Penalize if too few words
        word_count = len(markdown_content.split())
        if word_count < 20:
            score -= 20
        elif word_count < 50:
            score -= 10
        
        # Check for placeholder/error text
        error_indicators = ['error', 'could not', 'unable to', 'failed', 'corrupted']
        for indicator in error_indicators:
            if indicator.lower() in markdown_content[:200].lower():
                score -= 15
                break
        
        # Bonus for structured content (headings)
        if markdown_content.count('#') >= 2:
            score += 5
        
        # Bonus for lists
        if markdown_content.count('\n-') >= 3 or markdown_content.count('\n*') >= 3:
            score += 5
        
        return max(0, min(100, score))
    
    def _extract_author(self, docling_result):
        """Extract author from document"""
        try:
            if docling_result and hasattr(docling_result, 'document'):
                # Try to get author from document metadata
                if hasattr(docling_result.document, 'metadata'):
                    return docling_result.document.metadata.get('author', 'Unknown')
        except:
            pass
        return 'Unknown'
    
    def _extract_creation_date(self, docling_result):
        """Extract creation date from document"""
        try:
            if docling_result and hasattr(docling_result, 'document'):
                if hasattr(docling_result.document, 'metadata'):
                    return docling_result.document.metadata.get('creation_date', 'Unknown')
        except:
            pass
        return 'Unknown'
    
    def _extract_title(self, docling_result):
        """Extract title from document"""
        try:
            if docling_result and hasattr(docling_result, 'document'):
                if hasattr(docling_result.document, 'metadata'):
                    return docling_result.document.metadata.get('title', 'Unknown')
        except:
            pass
        return 'Unknown'
    
    def save_metadata(self, input_path, metadata):
        """
        Save metadata to JSON file
        
        Args:
            input_path: Input file path
            metadata: Metadata dictionary
        
        Returns:
            bool: True if successful
        """
        try:
            # Create metadata filename
            input_path = Path(input_path)
            metadata_filename = f"{input_path.stem}.json"
            metadata_path = Path(self.config.METADATA_DIR) / metadata_filename
            
            # Ensure directory exists
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"   [!] Could not save metadata: {e}")
            return False
    
    def load_metadata(self, input_path):
        """
        Load metadata from JSON file
        
        Args:
            input_path: Input file path
        
        Returns:
            dict: Metadata or None if not found
        """
        try:
            input_path = Path(input_path)
            metadata_filename = f"{input_path.stem}.json"
            metadata_path = Path(self.config.METADATA_DIR) / metadata_filename
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"   [!] Could not load metadata: {e}")
            return None
    
    def create_conversion_log(self, all_metadata):
        """
        Create comprehensive conversion log
        
        Args:
            all_metadata: List of all metadata dictionaries
        
        Returns:
            dict: Conversion log summary
        """
        log = {
            'conversion_date': datetime.now().isoformat(),
            'total_files': len(all_metadata),
            'total_size_bytes': sum(m['original_size_bytes'] for m in all_metadata),
            'total_markdown_size_bytes': sum(m['markdown_size_bytes'] for m in all_metadata),
            'average_quality_score': sum(m['conversion_quality_score'] for m in all_metadata) / len(all_metadata) if all_metadata else 0,
            'formats_processed': {},
            'files': all_metadata
        }
        
        # Count by format
        for metadata in all_metadata:
            fmt = metadata['original_format']
            log['formats_processed'][fmt] = log['formats_processed'].get(fmt, 0) + 1
        
        return log
    
    def save_conversion_log(self, conversion_log):
        """
        Save conversion log to file
        
        Args:
            conversion_log: Conversion log dictionary
        
        Returns:
            Path: Path to saved log
        """
        try:
            log_path = Path(self.config.METADATA_DIR) / 'conversion_log.json'
            
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(conversion_log, f, indent=2, ensure_ascii=False)
            
            print(f"[*] Conversion log saved: {log_path}")
            return log_path
            
        except Exception as e:
            print(f"[!] Could not save conversion log: {e}")
            return None