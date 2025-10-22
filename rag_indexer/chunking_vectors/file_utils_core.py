#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified core file utilities module for RAG Document Indexer (Part 2: Chunking & Vectors Only)
Contains only utility functions needed for markdown processing
SIMPLIFIED: Removed all document processing functions - only cleaning utilities remain
"""

import os
from pathlib import Path


def clean_content_from_null_bytes(content):
    """
    Clean content from null bytes and other problematic characters
    
    Args:
        content: Text content to clean
    
    Returns:
        str: Cleaned content
    """
    if not isinstance(content, str):
        return content
    
    # Remove null bytes (\u0000) and other problematic characters
    content = content.replace('\u0000', '').replace('\x00', '').replace('\x01', '').replace('\x02', '')
    
    # Remove control characters (except newlines and tabs)
    cleaned_content = ''.join(char for char in content 
                            if ord(char) >= 32 or char in '\n\t\r')
    
    return cleaned_content


def clean_metadata_recursive(obj):
    """
    Recursively clean metadata from null bytes
    
    Args:
        obj: Object to clean (dict, list, str, etc.)
    
    Returns:
        Cleaned object
    """
    if isinstance(obj, dict):
        return {k: clean_metadata_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_metadata_recursive(v) for v in obj]
    elif isinstance(obj, str):
        # Remove null bytes and limit string length
        cleaned = obj.replace('\u0000', '').replace('\x00', '')
        return cleaned[:1000]  # Limit metadata string length
    else:
        return obj


def normalize_file_path(file_path):
    """
    Normalize file path for comparison
    
    Args:
        file_path: File path to normalize
    
    Returns:
        str: Normalized file path
    """
    return os.path.normpath(os.path.abspath(file_path))


def validate_file_path(file_path):
    """
    Validate if file path exists and is readable
    
    Args:
        file_path: Path to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        if not os.path.isfile(file_path):
            return False, "Path is not a file"
        
        if not os.access(file_path, os.R_OK):
            return False, "File is not readable"
        
        return True, None
        
    except Exception as e:
        return False, f"Error accessing file: {e}"


def get_file_info(file_path):
    """
    Get basic information about a file
    
    Args:
        file_path: Path to the file
    
    Returns:
        dict: File information including size, extension, etc.
    """
    try:
        path_obj = Path(file_path)
        stat_info = os.stat(file_path)
        
        return {
            'name': path_obj.name,
            'stem': path_obj.stem,
            'suffix': path_obj.suffix.lower(),
            'size': stat_info.st_size,
            'size_mb': stat_info.st_size / (1024 * 1024),
            'modified': stat_info.st_mtime,
            'is_markdown': path_obj.suffix.lower() == '.md',
        }
    except Exception as e:
        return {'error': str(e)}


def is_blacklisted_directory(directory_path, blacklist_directories):
    """
    Check if a directory is in the blacklist and should be excluded
    
    Args:
        directory_path: Path to check
        blacklist_directories: List of blacklisted directory names
    
    Returns:
        bool: True if directory should be excluded
    """
    if not blacklist_directories:
        return False
    
    # Convert path to Path object for easier manipulation
    path_obj = Path(directory_path)
    
    # Get all parts of the path
    path_parts = path_obj.parts
    
    # Check if any part of the path matches blacklisted directories
    for blacklist_dir in blacklist_directories:
        if blacklist_dir in path_parts:
            return True
    
    # Also check the directory name itself
    if path_obj.name in blacklist_directories:
        return True
    
    return False


def should_skip_directory(directory_path, blacklist_directories=None, verbose=False):
    """
    Determine if a directory should be skipped during scanning
    
    Args:
        directory_path: Path to the directory
        blacklist_directories: List of blacklisted directory names
        verbose: Whether to print skip reasons
    
    Returns:
        tuple: (should_skip, reason)
    """
    path_obj = Path(directory_path)
    
    # Check if directory exists and is accessible
    if not path_obj.exists():
        return True, "Directory does not exist"
    
    if not path_obj.is_dir():
        return True, "Path is not a directory"
    
    if not os.access(path_obj, os.R_OK):
        return True, "Directory not readable"
    
    # Check blacklist
    if blacklist_directories and is_blacklisted_directory(directory_path, blacklist_directories):
        if verbose:
            print(f"   [*] Skipping blacklisted directory: {path_obj.name}")
        return True, f"Directory '{path_obj.name}' is blacklisted"
    
    return False, None


def scan_files_in_directory(directory, recursive=True, blacklist_directories=None, verbose=False):
    """
    Scan directory to get all MARKDOWN files (.md) with blacklist filtering

    Args:
        directory: Directory to scan
        recursive: Whether to scan recursively
        blacklist_directories: List of directory names to exclude
        verbose: Whether to print detailed scanning info

    Returns:
        list: List of .md file paths (excludes blacklisted directories)
    """
    file_list = []
    skipped_dirs = []

    try:
        if verbose:
            print(f"[*] Scanning directory: {directory}")
            if blacklist_directories:
                print(f"[*] Blacklisted directories: {', '.join(blacklist_directories)}")

        if recursive:
            # Use os.walk for better control over directory traversal
            for root, dirs, files in os.walk(directory):
                # Filter out blacklisted directories from dirs list
                # This prevents os.walk from entering them
                original_dirs = dirs.copy()
                dirs[:] = []  # Clear the list

                for dir_name in original_dirs:
                    dir_path = os.path.join(root, dir_name)
                    should_skip, reason = should_skip_directory(dir_path, blacklist_directories, verbose)

                    if should_skip:
                        skipped_dirs.append((dir_path, reason))
                    else:
                        dirs.append(dir_name)  # Add back to dirs for traversal

                # Add ONLY .md files from current directory
                for file_name in files:
                    # [*] FIXED: Filter only .md files
                    if file_name.lower().endswith('.md'):
                        file_path = os.path.join(root, file_name)
                        file_list.append(file_path)
        else:
            # Non-recursive scan
            directory_path = Path(directory)
            for item in directory_path.iterdir():
                # [*] FIXED: Filter only .md files
                if item.is_file() and item.suffix.lower() == '.md':
                    file_list.append(str(item))
        
        if verbose and skipped_dirs:
            print(f"[*] Skipped {len(skipped_dirs)} blacklisted directories:")
            for skipped_dir, reason in skipped_dirs[:5]:  # Show first 5
                print(f"   - {Path(skipped_dir).name}: {reason}")
            if len(skipped_dirs) > 5:
                print(f"   ... and {len(skipped_dirs) - 5} more")
        
        if verbose:
            print(f"[*] Found {len(file_list)} files total")
    
    except Exception as e:
        print(f"[-] ERROR: Failed to scan directory {directory}: {e}")
    
    return file_list


def ensure_directory_exists(directory_path):
    """
    Ensure a directory exists, create if necessary
    
    Args:
        directory_path: Path to directory
    
    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"ERROR: Could not create directory {directory_path}: {e}")
        return False


if __name__ == "__main__":
    # Test simplified utilities when run directly
    print("[*] Simplified File Utilities - Part 2: Chunking & Vectors Only")
    print("=" * 60)
    
    # Test content cleaning
    test_content = "Hello\x00World\x01Test"
    cleaned = clean_content_from_null_bytes(test_content)
    print(f"Content cleaning test:")
    print(f"  Original: {repr(test_content)}")
    print(f"  Cleaned: {repr(cleaned)}")
    
    # Test metadata cleaning
    test_metadata = {
        'name': 'test\x00file',
        'path': '/path/to\x00/file',
        'nested': {
            'key': 'value\x00clean'
        }
    }
    cleaned_metadata = clean_metadata_recursive(test_metadata)
    print(f"\nMetadata cleaning test:")
    print(f"  Original: {test_metadata}")
    print(f"  Cleaned: {cleaned_metadata}")
    
    print("\n[+] Simplified utilities for markdown processing ready")
    print("=" * 60)