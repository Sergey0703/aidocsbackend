#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for Docling module
"""

import os
from pathlib import Path


def ensure_directory_exists(directory_path):
    """
    Ensure a directory exists, create if necessary
    
    Args:
        directory_path: Path to directory
    
    Returns:
        bool: True if directory exists or was created
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"ERROR: Could not create directory {directory_path}: {e}")
        return False


def safe_write_file(file_path, content, encoding='utf-8'):
    """
    Safely write content to file
    
    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
    
    Returns:
        bool: True if successful
    """
    try:
        # Ensure directory exists
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"ERROR: Could not write to {file_path}: {e}")
        return False


def format_time(seconds):
    """
    Format seconds into human-readable time
    
    Args:
        seconds: Number of seconds
    
    Returns:
        str: Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_size(bytes_size):
    """
    Format bytes into human-readable size
    
    Args:
        bytes_size: Size in bytes
    
    Returns:
        str: Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"


def get_file_extension(file_path):
    """
    Get file extension without dot
    
    Args:
        file_path: Path to file
    
    Returns:
        str: File extension (lowercase, no dot)
    """
    return Path(file_path).suffix.lower().lstrip('.')


def get_relative_path(file_path, base_path):
    """
    Get relative path from base
    
    Args:
        file_path: File path
        base_path: Base directory path
    
    Returns:
        Path: Relative path
    """
    try:
        return Path(file_path).relative_to(base_path)
    except ValueError:
        return Path(file_path).name