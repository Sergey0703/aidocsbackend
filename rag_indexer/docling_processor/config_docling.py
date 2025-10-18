#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for Docling Document Conversion
Handles settings for converting raw documents to markdown
"""

import os
from pathlib import Path
from dotenv import load_dotenv


class DoclingConfig:
    """Configuration for Docling document conversion"""
    
    def __init__(self):
        """Initialize configuration by loading environment variables"""
        load_dotenv()
        self._load_settings()
        self._validate_settings()
    
    def _load_settings(self):
        """Load all settings from environment variables with defaults"""
        
        # --- DIRECTORY SETTINGS ---
        # Default all paths to the rag_indexer/data tree
        base_dir = Path(__file__).resolve().parent.parent / "data"
        self.RAW_DOCUMENTS_DIR = os.getenv("RAW_DOCUMENTS_DIR", str(base_dir / "raw"))
        self.MARKDOWN_OUTPUT_DIR = os.getenv("MARKDOWN_OUTPUT_DIR", str(base_dir / "markdown"))
        self.FAILED_CONVERSIONS_DIR = os.getenv("FAILED_CONVERSIONS_DIR", str(base_dir / "failed"))
        self.METADATA_DIR = os.getenv("METADATA_DIR", str(base_dir / "markdown" / "_metadata"))
        
        # --- SUPPORTED FORMATS ---
        default_formats = "pdf,docx,doc,pptx,ppt,txt,html,htm,png,jpg,jpeg,tiff"
        formats_env = os.getenv("SUPPORTED_FORMATS", default_formats)
        self.SUPPORTED_FORMATS = [fmt.strip().lower() for fmt in formats_env.split(",")]
        
        # --- CONVERSION SETTINGS ---
        self.RECURSIVE_SCAN = os.getenv("RECURSIVE_SCAN", "true").lower() == "true"
        self.MIRROR_DIRECTORY_STRUCTURE = os.getenv("MIRROR_DIRECTORY_STRUCTURE", "true").lower() == "true"
        self.PRESERVE_IMAGES = os.getenv("PRESERVE_IMAGES", "false").lower() == "true"
        self.EXTRACT_TABLES = os.getenv("EXTRACT_TABLES", "true").lower() == "true"
        
        # --- OCR SETTINGS ---
        self.ENABLE_OCR = os.getenv("ENABLE_OCR", "true").lower() == "true"
        self.OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
        
        # --- NAMING CONVENTION ---
        # Format: timestamp_originalname.md
        self.USE_TIMESTAMP_PREFIX = os.getenv("USE_TIMESTAMP_PREFIX", "false").lower() == "true"
        self.TIMESTAMP_FORMAT = os.getenv("TIMESTAMP_FORMAT", "%Y%m%d_%H%M%S")
        
        # --- ERROR HANDLING ---
        self.SKIP_FAILED_CONVERSIONS = os.getenv("SKIP_FAILED_CONVERSIONS", "true").lower() == "true"
        self.RETRY_FAILED = os.getenv("RETRY_FAILED", "false").lower() == "true"
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
        
        # --- PERFORMANCE ---
        self.BATCH_SIZE = int(os.getenv("DOCLING_BATCH_SIZE", "5"))
        self.USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"
        self.MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        
        # --- LOGGING ---
        self.VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "true").lower() == "true"
        # Keep logs at project root by default
        project_root = Path(__file__).resolve().parents[2]
        self.LOG_DIR = os.getenv("LOG_DIR", str(project_root / "logs"))
    
    def _validate_settings(self):
        """Validate configuration settings"""
        
        # Check input directory exists
        if not os.path.exists(self.RAW_DOCUMENTS_DIR):
            print(f"⚠️ WARNING: Input directory does not exist: {self.RAW_DOCUMENTS_DIR}")
            print(f"Creating directory...")
            Path(self.RAW_DOCUMENTS_DIR).mkdir(parents=True, exist_ok=True)
        
        # Ensure output directories exist
        Path(self.MARKDOWN_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.FAILED_CONVERSIONS_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.METADATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)
        
        # Validate batch size
        if self.BATCH_SIZE < 1:
            raise ValueError("DOCLING_BATCH_SIZE must be at least 1")
        
        # Validate max file size
        if self.MAX_FILE_SIZE_MB < 1:
            raise ValueError("MAX_FILE_SIZE_MB must be at least 1")
    
    def print_config(self):
        """Print current configuration"""
        print("=" * 60)
        print("🔧 DOCLING CONVERSION CONFIGURATION")
        print("=" * 60)
        print(f"Input directory: {self.RAW_DOCUMENTS_DIR}")
        print(f"Output directory: {self.MARKDOWN_OUTPUT_DIR}")
        print(f"Metadata directory: {self.METADATA_DIR}")
        print(f"Failed conversions: {self.FAILED_CONVERSIONS_DIR}")
        print(f"\nSupported formats: {', '.join(self.SUPPORTED_FORMATS)}")
        print(f"Recursive scan: {'✓' if self.RECURSIVE_SCAN else '✗'}")
        print(f"Mirror structure: {'✓' if self.MIRROR_DIRECTORY_STRUCTURE else '✗'}")
        print(f"OCR enabled: {'✓' if self.ENABLE_OCR else '✗'}")
        print(f"Extract tables: {'✓' if self.EXTRACT_TABLES else '✗'}")
        print(f"\nBatch size: {self.BATCH_SIZE}")
        print(f"Max file size: {self.MAX_FILE_SIZE_MB} MB")
        print(f"GPU acceleration: {'✓' if self.USE_GPU else '✗'}")
        print("=" * 60)
    
    def is_supported_format(self, file_path):
        """
        Check if file format is supported
        
        Args:
            file_path: Path to file
        
        Returns:
            bool: True if format is supported
        """
        ext = Path(file_path).suffix.lower().lstrip('.')
        return ext in self.SUPPORTED_FORMATS
    
    def get_output_path(self, input_path, timestamp=None):
        """
        Get output markdown path for input file
        
        Args:
            input_path: Input file path
            timestamp: Optional timestamp string
        
        Returns:
            Path: Output markdown file path
        """
        input_path = Path(input_path)
        
        # Get relative path from RAW_DOCUMENTS_DIR
        try:
            rel_path = input_path.relative_to(self.RAW_DOCUMENTS_DIR)
        except ValueError:
            # If not relative to RAW_DOCUMENTS_DIR, use just the filename
            rel_path = Path(input_path.name)
        
        # Build output path
        if self.MIRROR_DIRECTORY_STRUCTURE:
            # Mirror directory structure
            output_dir = Path(self.MARKDOWN_OUTPUT_DIR) / rel_path.parent
        else:
            # Flat structure
            output_dir = Path(self.MARKDOWN_OUTPUT_DIR)
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build filename
        stem = input_path.stem
        
        if self.USE_TIMESTAMP_PREFIX and timestamp:
            filename = f"{timestamp}_{stem}.md"
        else:
            filename = f"{stem}.md"
        
        return output_dir / filename


def get_docling_config():
    """Get global Docling configuration instance"""
    return DoclingConfig()


if __name__ == "__main__":
    # Test configuration
    config = get_docling_config()
    config.print_config()