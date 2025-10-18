#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Dynamic Two-Level Master RAG Document Indexer Controller
Dynamically discovers year directories and processes numbered subdirectories within each
ENHANCED LOGGING: Captures and preserves detailed output from indexer.py

This script:
- Scans root directory and dynamically discovers ANY year directories (2015, 2018, 2025, etc.)
- Within each discovered year, scans for numbered subdirectories (1, 2, 3, etc.)
- EXCLUDES service directories (doc_backups, logs, etc.) from processing
- For each numbered subdirectory, sets DOCUMENTS_DIR and calls indexer.py
- ENHANCED: Captures detailed output and creates comprehensive logs
- Processes: ./data/634/YYYY/N for whatever YYYY and N actually exist

Usage:
   python master_indexer.py

Configuration:
   Set MASTER_DOCUMENTS_DIR in .env file or modify the default path below
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


# Service directories to exclude from processing
EXCLUDED_DIRECTORIES = [
   'doc_backups',     # Backup directory for converted .doc files
   'logs',            # Log files directory
   'temp',            # Temporary files directory
   'cache',           # Cache files
   '.git',            # Git repository directory
   '__pycache__',     # Python cache directory
   '.vscode',         # VS Code settings
   '.idea',           # IntelliJ IDEA settings
   'node_modules',    # Node.js modules
   '.env',            # Environment files
   'backup',          # Generic backup directories
   'backups',         # Alternative backup naming
   'tmp',             # Alternative temp naming
   '.tmp'             # Hidden temp directories
]


def log_master_message(message, log_file_path="./logs/master_indexer.log"):
    """
    Log master indexer messages with timestamps
    
    Args:
        message: Message to log
        log_file_path: Path to master log file
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    try:
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"WARNING: Could not write to master log: {e}")
    
    # Also print to console
    print(f"[MASTER] {message}")


def save_detailed_indexer_output(directory_identifier, stdout, stderr, return_code, processing_time, log_dir="./logs"):
    """
    Save detailed indexer output to individual log files
    
    Args:
        directory_identifier: Directory identifier (e.g., "2016/3")
        stdout: Standard output from indexer
        stderr: Standard error from indexer
        return_code: Return code from indexer
        processing_time: Processing time in seconds
        log_dir: Directory for log files
    
    Returns:
        str: Path to detailed log file
    """
    try:
        # Ensure logs directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create safe filename
        safe_identifier = directory_identifier.replace('/', '_').replace('\\', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"indexer_detailed_{safe_identifier}_{timestamp}.log")
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"DETAILED INDEXER OUTPUT FOR: {directory_identifier}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Processing time: {processing_time:.2f} seconds\n")
            f.write(f"Return code: {return_code}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("STANDARD OUTPUT:\n")
            f.write("-" * 40 + "\n")
            if stdout:
                f.write(stdout)
            else:
                f.write("(No standard output)\n")
            f.write("\n" + "-" * 40 + "\n\n")
            
            f.write("STANDARD ERROR:\n")
            f.write("-" * 40 + "\n")
            if stderr:
                f.write(stderr)
            else:
                f.write("(No error output)\n")
            f.write("\n" + "-" * 40 + "\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("END OF DETAILED OUTPUT\n")
            f.write("=" * 80 + "\n")
        
        return log_file
        
    except Exception as e:
        log_master_message(f"WARNING: Could not save detailed output for {directory_identifier}: {e}")
        return None


def extract_key_metrics_from_output(stdout):
    """
    Extract key metrics from indexer output for enhanced logging
    
    Args:
        stdout: Standard output from indexer
    
    Returns:
        dict: Extracted metrics
    """
    metrics = {
        'documents_loaded': None,
        'chunks_created': None,
        'records_saved': None,
        'success_rate': None,
        'processing_time': None,
        'conversion_results': {},
        'pdf_stats': {},
        'ocr_stats': {},
        'errors': [],
        'warnings': [],
        'dependency_issues': [],
        'critical_errors': []
    }
    
    if not stdout:
        return metrics
    
    lines = stdout.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Extract key numbers
        if 'Documents loaded:' in line or 'documents loaded:' in line:
            try:
                metrics['documents_loaded'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        elif 'Chunks created:' in line or 'chunks created:' in line:
            try:
                metrics['chunks_created'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        elif 'Records saved:' in line or 'records saved:' in line:
            try:
                metrics['records_saved'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        elif 'Success rate:' in line or 'success rate:' in line:
            try:
                rate_str = line.split(':')[-1].strip().replace('%', '')
                metrics['success_rate'] = float(rate_str)
            except:
                pass
        
        elif 'Total time:' in line or 'Processing time:' in line:
            try:
                time_part = line.split(':')[-1].strip()
                if 's' in time_part:
                    metrics['processing_time'] = float(time_part.replace('s', '').strip())
            except:
                pass
        
        # Conversion results
        elif 'Successfully converted:' in line:
            try:
                metrics['conversion_results']['successful'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        elif 'Failed conversions:' in line:
            try:
                metrics['conversion_results']['failed'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        # PDF processing stats
        elif 'PDF files processed:' in line:
            try:
                metrics['pdf_stats']['files_processed'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        elif 'Total pages:' in line and 'PDF' in line:
            try:
                metrics['pdf_stats']['total_pages'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        # OCR stats
        elif 'Images processed:' in line:
            try:
                metrics['ocr_stats']['images_processed'] = int(line.split(':')[-1].strip().replace(',', ''))
            except:
                pass
        
        elif 'OCR success rate:' in line:
            try:
                rate_str = line.split(':')[-1].strip().replace('%', '')
                metrics['ocr_stats']['success_rate'] = float(rate_str)
            except:
                pass
        
        # ENHANCED ERROR DETECTION
        line_lower = line.lower()
        
        # Critical errors that stop processing
        if any(critical in line_lower for critical in ['fatal error', 'critical error', 'failed to', 'could not']):
            metrics['critical_errors'].append(line)
        
        # Dependency issues
        elif any(dep_issue in line_lower for dep_issue in ['missing optional dependency', 'install', 'not available', 'not installed']):
            metrics['dependency_issues'].append(line)
        
        # General errors
        elif line_lower.startswith('error:') or 'error:' in line_lower or line_lower.startswith('‚ùå'):
            metrics['errors'].append(line)
        
        # Warnings
        elif line_lower.startswith('warning:') or 'warning:' in line_lower or line_lower.startswith('‚ö†Ô∏è'):
            metrics['warnings'].append(line)
    
    return metrics


def log_enhanced_summary(directory_identifier, metrics, processing_time, return_code):
    """
    Log enhanced summary with extracted metrics
    
    Args:
        directory_identifier: Directory identifier
        metrics: Extracted metrics from indexer output
        processing_time: Processing time
        return_code: Return code
    """
    log_master_message(f"")
    log_master_message(f"Ì†ΩÌ≥ä ENHANCED PROCESSING SUMMARY FOR: {directory_identifier}")
    log_master_message(f"‚è±Ô∏è Processing time: {processing_time:.1f}s")
    log_master_message(f"Ì†ΩÌ¥Ñ Return code: {return_code}")
    
    # Document processing
    if metrics['documents_loaded'] is not None:
        log_master_message(f"Ì†ΩÌ≥Ñ Documents loaded: {metrics['documents_loaded']:,}")
    
    if metrics['chunks_created'] is not None:
        log_master_message(f"Ì†æÌ∑© Chunks created: {metrics['chunks_created']:,}")
    
    if metrics['records_saved'] is not None:
        log_master_message(f"Ì†ΩÌ≤æ Records saved: {metrics['records_saved']:,}")
    
    if metrics['success_rate'] is not None:
        log_master_message(f"‚úÖ Success rate: {metrics['success_rate']:.1f}%")
    
    # Conversion results
    if metrics['conversion_results']:
        conv = metrics['conversion_results']
        if 'successful' in conv or 'failed' in conv:
            successful = conv.get('successful', 0)
            failed = conv.get('failed', 0)
            log_master_message(f"Ì†ΩÌ¥Ñ Document conversion: {successful} successful, {failed} failed")
    
    # PDF processing
    if metrics['pdf_stats']:
        pdf = metrics['pdf_stats']
        if 'files_processed' in pdf:
            log_master_message(f"Ì†ΩÌ≥ë PDF files processed: {pdf['files_processed']}")
        if 'total_pages' in pdf:
            log_master_message(f"Ì†ΩÌ≥Ñ Total PDF pages: {pdf['total_pages']:,}")
    
    # OCR processing
    if metrics['ocr_stats']:
        ocr = metrics['ocr_stats']
        if 'images_processed' in ocr:
            log_master_message(f"Ì†ΩÌ∂ºÔ∏è Images processed: {ocr['images_processed']}")
        if 'success_rate' in ocr:
            log_master_message(f"Ì†ΩÌ¥ç OCR success rate: {ocr['success_rate']:.1f}%")
    
    # ENHANCED ERROR REPORTING
    if metrics['critical_errors']:
        log_master_message(f"Ì†ΩÌ∫® CRITICAL ERRORS: {len(metrics['critical_errors'])}")
        for error in metrics['critical_errors']:
            log_master_message(f"   Ì†ΩÌ∫® {error}")
    
    if metrics['dependency_issues']:
        log_master_message(f"Ì†ΩÌ≥¶ DEPENDENCY ISSUES: {len(metrics['dependency_issues'])}")
        for issue in metrics['dependency_issues']:
            log_master_message(f"   Ì†ΩÌ≥¶ {issue}")
    
    # Errors and warnings
    if metrics['errors']:
        log_master_message(f"‚ùå Errors found: {len(metrics['errors'])}")
        for error in metrics['errors'][:3]:  # Show first 3 errors
            log_master_message(f"   ‚ùå {error}")
        if len(metrics['errors']) > 3:
            log_master_message(f"   ... and {len(metrics['errors']) - 3} more errors")
    
    if metrics['warnings']:
        log_master_message(f"‚ö†Ô∏è Warnings: {len(metrics['warnings'])}")
        for warning in metrics['warnings'][:2]:  # Show first 2 warnings
            log_master_message(f"   ‚ö†Ô∏è {warning}")
        if len(metrics['warnings']) > 2:
            log_master_message(f"   ... and {len(metrics['warnings']) - 2} more warnings")


def is_excluded_directory(directory_name):
    """
    Check if directory should be excluded from processing
    
    Args:
        directory_name: Name of directory to check
    
    Returns:
        tuple: (is_excluded, reason)
    """
    directory_name_lower = directory_name.lower()
    
    # Check against excluded directories list
    for excluded in EXCLUDED_DIRECTORIES:
        if directory_name_lower == excluded.lower():
            return True, f"Service directory ({excluded})"
    
    # Check for backup directory patterns
    backup_patterns = ['backup', 'bak', 'old', 'archive', 'temp', 'tmp']
    if any(pattern in directory_name_lower for pattern in backup_patterns):
        return True, f"Backup pattern directory"
    
    # Hidden directories
    if directory_name.startswith('.'):
        return True, "Hidden directory"
    
    return False, None


def has_files_in_directory(directory_path):
    """
    Quick check if directory has any files
    
    Args:
        directory_path: Path to directory to check
    
    Returns:
        tuple: (has_files, file_count)
    """
    try:
        file_count = 0
        for root, dirs, files in os.walk(directory_path):
            file_count += len(files)
            # Quick check - if we find files, we can return early
            if file_count > 0:
                return True, file_count
            # Don't go too deep for performance
            if file_count > 10:
                break
        return file_count > 0, file_count
    except Exception:
        return False, 0


def discover_year_directories(root_path):
    """
    Dynamically discover all year directories in root path
    
    Args:
        root_path: Root directory to scan (e.g., ./data/634)
    
    Returns:
        list: List of discovered year directory paths
    """
    year_directories = []
    
    try:
        root_path_obj = Path(root_path)
        
        if not root_path_obj.exists():
            log_master_message(f"ERROR: Root path does not exist: {root_path}")
            return []
        
        log_master_message(f"Dynamically discovering year directories in: {root_path}")
        
        # Scan for any directories that could be years or other valid containers
        for item in root_path_obj.iterdir():
            if item.is_dir():
                directory_name = item.name
                
                # Check if directory should be excluded
                is_excluded, reason = is_excluded_directory(directory_name)
                if is_excluded:
                    log_master_message(f"EXCLUDED YEAR DIR: {directory_name} - {reason}")
                    continue
                
                # Check if directory is accessible
                if not os.access(str(item), os.R_OK):
                    log_master_message(f"EXCLUDED YEAR DIR: {directory_name} - No read permission")
                    continue
                
                # Add to year directories list
                year_directories.append(str(item))
                log_master_message(f"DISCOVERED YEAR DIR: {directory_name}")
        
        # Sort year directories for consistent processing order
        year_directories.sort()
        
        log_master_message(f"YEAR DISCOVERY COMPLETE:")
        log_master_message(f"  Total year directories found: {len(year_directories)}")
        
        if year_directories:
            log_master_message("  Year directories discovered:")
            for i, year_dir in enumerate(year_directories, 1):
                year_name = os.path.basename(year_dir)
                log_master_message(f"    {i}. {year_name}")
        
        return year_directories
        
    except Exception as e:
        log_master_message(f"ERROR: Failed to discover year directories: {e}")
        return []


def discover_numbered_subdirectories(year_directory_path):
    """
    Dynamically discover numbered subdirectories within a year directory
    
    Args:
        year_directory_path: Path to year directory
    
    Returns:
        list: List of numbered subdirectory paths with files
    """
    numbered_subdirectories = []
    year_name = os.path.basename(year_directory_path)
    
    try:
        year_path_obj = Path(year_directory_path)
        
        log_master_message(f"  Scanning year {year_name} for numbered subdirectories...")
        
        # Scan for subdirectories
        for item in year_path_obj.iterdir():
            if item.is_dir():
                subdir_name = item.name
                
                # Check if subdirectory should be excluded
                is_excluded, reason = is_excluded_directory(subdir_name)
                if is_excluded:
                    log_master_message(f"    EXCLUDED: {year_name}/{subdir_name} - {reason}")
                    continue
                
                # Check if subdirectory is accessible
                if not os.access(str(item), os.R_OK):
                    log_master_message(f"    EXCLUDED: {year_name}/{subdir_name} - No read permission")
                    continue
                
                # Check if subdirectory has files
                has_files, file_count = has_files_in_directory(str(item))
                if not has_files:
                    log_master_message(f"    EXCLUDED: {year_name}/{subdir_name} - No files found")
                    continue
                
                # Add to numbered subdirectories list
                numbered_subdirectories.append(str(item))
                log_master_message(f"    FOUND: {year_name}/{subdir_name} ({file_count} files)")
        
        # Sort for consistent processing order (numeric sort if possible)
        def sort_key(path):
            name = os.path.basename(path)
            # Try to sort numerically, fall back to string sort
            try:
                return int(name)
            except ValueError:
                return name
        
        numbered_subdirectories.sort(key=sort_key)
        
        log_master_message(f"  Year {year_name} scan complete: {len(numbered_subdirectories)} valid subdirectories")
        
        return numbered_subdirectories
        
    except Exception as e:
        log_master_message(f"ERROR: Failed to scan year directory {year_directory_path}: {e}")
        return []


def discover_all_processing_directories(root_path):
    """
    Dynamically discover all directories to process (Year/Number structure)
    
    Args:
        root_path: Root directory to scan
    
    Returns:
        list: List of all numbered subdirectory paths to process
    """
    all_processing_directories = []
    
    # Step 1: Discover year directories
    year_directories = discover_year_directories(root_path)
    
    if not year_directories:
        log_master_message(f"No year directories found in {root_path}")
        return []
    
    # Step 2: For each year, discover numbered subdirectories
    for year_directory in year_directories:
        year_name = os.path.basename(year_directory)
        log_master_message(f"Discovering subdirectories in year: {year_name}")
        
        numbered_subdirs = discover_numbered_subdirectories(year_directory)
        all_processing_directories.extend(numbered_subdirs)
    
    log_master_message(f"")
    log_master_message(f"COMPLETE DISCOVERY SUMMARY:")
    log_master_message(f"  Years scanned: {len(year_directories)}")
    log_master_message(f"  Total processing directories found: {len(all_processing_directories)}")
    
    if all_processing_directories:
        log_master_message(f"  All directories to process:")
        for i, proc_dir in enumerate(all_processing_directories, 1):
            # Create readable path (Year/Number)
            parts = Path(proc_dir).parts
            if len(parts) >= 2:
                display_path = f"{parts[-2]}/{parts[-1]}"
            else:
                display_path = os.path.basename(proc_dir)
            log_master_message(f"    {i}. {display_path}")
    
    return all_processing_directories


def process_single_directory(directory_path, directory_index, total_directories):
    """
    Process a single numbered directory by calling indexer.py with ENHANCED logging
    
    Args:
        directory_path: Path to the numbered directory to process
        directory_index: Current directory index (1-based)
        total_directories: Total number of directories to process
    
    Returns:
        tuple: (success, processing_time, error_message, detailed_log_path)
    """
    # Create readable directory identifier (Year/Number)
    parts = Path(directory_path).parts
    if len(parts) >= 2:
        directory_identifier = f"{parts[-2]}/{parts[-1]}"
    else:
        directory_identifier = os.path.basename(directory_path)
    
    log_master_message(f"")
    log_master_message(f"{'='*80}")
    log_master_message(f"Ì†ΩÌ∫Ä PROCESSING DIRECTORY {directory_index}/{total_directories}: {directory_identifier}")
    log_master_message(f"Ì†ΩÌ≥Å Full path: {directory_path}")
    log_master_message(f"{'='*80}")
    
    # Create environment for subprocess
    env = os.environ.copy()
    env['DOCUMENTS_DIR'] = directory_path
    
    # Log the backup directory that will be used
    backup_dir = env.get('DOC_BACKUP_ABSOLUTE_PATH', 'Default (parent/doc_backups)')
    log_master_message(f"Ì†ΩÌ≤æ Backup directory: {backup_dir}")
    
    start_time = time.time()
    error_message = None
    detailed_log_path = None
    
    try:
        log_master_message(f"Ì†ΩÌ∫Ä Launching indexer.py for directory: {directory_identifier}")
        
        # Run indexer.py as subprocess
        result = subprocess.run(
            [sys.executable, "indexer.py"],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,  # Capture output for logging
            text=True,
            timeout=7200  # 1 hour timeout per directory
        )
        
        processing_time = time.time() - start_time
        
        # ENHANCED: Save complete detailed output
        detailed_log_path = save_detailed_indexer_output(
            directory_identifier, 
            result.stdout, 
            result.stderr, 
            result.returncode, 
            processing_time
        )
        
        if detailed_log_path:
            log_master_message(f"Ì†ΩÌ≥ã Detailed output saved to: {os.path.basename(detailed_log_path)}")
        
        # ENHANCED: Extract key metrics from output
        metrics = extract_key_metrics_from_output(result.stdout)
        
        # ENHANCED: Log enhanced summary with extracted metrics
        log_enhanced_summary(directory_identifier, metrics, processing_time, result.returncode)
        
        # ENHANCED: Log important output lines including errors and warnings
        if result.stdout:
            stdout_lines = result.stdout.split('\n')
            
            # 1. ERRORS AND WARNINGS (HIGHEST PRIORITY)
            error_warning_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in 
                                 ['error:', 'warning:', 'failed:', 'exception:', 'missing', 'not found', 'could not', 'cannot', 'unable to'])]
            
            if error_warning_lines:
                log_master_message(f"Ì†ΩÌ∫® ERRORS AND WARNINGS for {directory_identifier}:")
                for line in error_warning_lines:
                    if line.strip():
                        # Determine if it's error or warning
                        if any(err_word in line.lower() for err_word in ['error:', 'failed:', 'exception:', 'fatal']):
                            log_master_message(f"   ‚ùå {line.strip()}")
                        else:
                            log_master_message(f"   ‚ö†Ô∏è {line.strip()}")
            
            # 2. Show configuration and setup lines
            setup_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in 
                         ['configuration', 'documents directory', 'backup directory', 'enhanced features', 'loading enhanced'])]
            
            if setup_lines:
                log_master_message(f"‚öôÔ∏è SETUP INFORMATION for {directory_identifier}:")
                for line in setup_lines[:5]:  # First 5 setup lines
                    if line.strip():
                        log_master_message(f"   {line.strip()}")
            
            # 3. Show processing progress lines
            progress_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in 
                            ['loading', 'processing', 'chunk', 'embedding', 'batch', 'completed', 'successfully loaded', 'created'])]
            
            # Filter out lines already shown in errors section
            progress_lines = [line for line in progress_lines if not any(err_word in line.lower() for err_word in 
                            ['error:', 'warning:', 'failed:', 'exception:', 'missing', 'not found'])]
            
            if progress_lines:
                log_master_message(f"‚ö° PROCESSING PROGRESS for {directory_identifier}:")
                for line in progress_lines[-8:]:  # Last 8 progress lines
                    if line.strip():
                        log_master_message(f"   {line.strip()}")
            
            # 4. Show final results
            result_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in 
                          ['success', 'completed', 'final', 'summary', 'ready for rag queries', 'indexing completed'])]
            
            # Filter out lines already shown in errors section
            result_lines = [line for line in result_lines if not any(err_word in line.lower() for err_word in 
                          ['error:', 'warning:', 'failed:', 'exception:'])]
            
            if result_lines:
                log_master_message(f"‚úÖ FINAL RESULTS for {directory_identifier}:")
                for line in result_lines[-5:]:  # Last 5 result lines
                    if line.strip():
                        log_master_message(f"   {line.strip()}")
            
            # 5. DEPENDENCY ISSUES (Special handling)
            dependency_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in 
                              ['install', 'pip install', 'missing optional dependency', 'not available', 'conda'])]
            
            if dependency_lines:
                log_master_message(f"Ì†ΩÌ≥¶ DEPENDENCY ISSUES for {directory_identifier}:")
                for line in dependency_lines:
                    if line.strip():
                        log_master_message(f"   Ì†ΩÌ≥¶ {line.strip()}")
        
        # Log any errors from stderr
        if result.stderr:
            stderr_lines = result.stderr.split('\n')
            for line in stderr_lines[-5:]:  # Last 5 error lines
                if line.strip():
                    log_master_message(f"   ‚ùå STDERR: {line.strip()}")
        
        if result.returncode == 0:
            log_master_message(f"‚úÖ SUCCESS: Directory {directory_identifier} processed successfully in {processing_time:.1f}s")
            return True, processing_time, None, detailed_log_path
        else:
            error_message = f"indexer.py returned code {result.returncode}"
            log_master_message(f"‚ùå ERROR: Directory {directory_identifier} processing failed: {error_message}")
            return False, processing_time, error_message, detailed_log_path
            
    except subprocess.TimeoutExpired:
        processing_time = time.time() - start_time
        error_message = f"Processing timed out after {processing_time/60:.1f} minutes"
        log_master_message(f"‚è∞ TIMEOUT: Directory {directory_identifier} processing timed out")
        return False, processing_time, error_message, detailed_log_path
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_message = str(e)
        log_master_message(f"Ì†ΩÌ≤• EXCEPTION: Error processing {directory_identifier}: {e}")
        return False, processing_time, error_message, detailed_log_path


def create_final_summary(total_directories, successful_directories, failed_directories, 
                       total_time, processing_details, year_directories_found):
    """
    Create final processing summary with enhanced details
    
    Args:
        total_directories: Total directories processed
        successful_directories: Number of successful directories
        failed_directories: Number of failed directories
        total_time: Total processing time in seconds
        processing_details: List of processing details for each directory
        year_directories_found: Number of year directories discovered
    """
    log_master_message(f"")
    log_master_message(f"{'='*80}")
    log_master_message(f"Ì†ºÌøÅ ENHANCED DYNAMIC MASTER INDEXER FINAL SUMMARY")
    log_master_message(f"{'='*80}")
    
    # Discovery statistics
    log_master_message(f"Ì†ΩÌ¥ç Dynamic Discovery Results:")
    log_master_message(f"  Year directories discovered: {year_directories_found}")
    log_master_message(f"  Numbered directories found: {total_directories}")
    
    # Processing statistics
    log_master_message(f"Ì†ΩÌ≥ä Processing Statistics:")
    log_master_message(f"  Directories processed: {total_directories}")
    log_master_message(f"  Successful directories: {successful_directories}")
    log_master_message(f"  Failed directories: {failed_directories}")
    
    if total_directories > 0:
        success_rate = (successful_directories / total_directories * 100)
        log_master_message(f"  Success rate: {success_rate:.1f}%")
    else:
        log_master_message(f"  Success rate: 0%")
    
    log_master_message(f"  Total processing time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
    if total_directories > 0:
        avg_time = total_time / total_directories
        log_master_message(f"  Average time per directory: {avg_time:.1f} seconds")
    
    # Performance insights
    if processing_details:
        successful_details = [d for d in processing_details if d['success']]
        if successful_details:
            processing_times = [d['processing_time'] for d in successful_details]
            fastest_time = min(processing_times)
            slowest_time = max(processing_times)
            
            log_master_message(f"  ‚ö° Performance Insights:")
            log_master_message(f"    Fastest directory: {fastest_time:.1f}s")
            log_master_message(f"    Slowest directory: {slowest_time:.1f}s")
            
            # Find fastest and slowest directories
            fastest_dir = min(successful_details, key=lambda x: x['processing_time'])
            slowest_dir = max(successful_details, key=lambda x: x['processing_time'])
            log_master_message(f"    Fastest: {fastest_dir['directory_identifier']}")
            log_master_message(f"    Slowest: {slowest_dir['directory_identifier']}")
    
    # Enhanced logging information
    log_master_message(f"")
    log_master_message(f"Ì†ΩÌ≥ã Enhanced Logging Information:")
    log_master_message(f"  Master processing log: ./logs/master_indexer.log")
    log_master_message(f"  Individual detailed logs: ./logs/indexer_detailed_*.log")
    log_master_message(f"  Individual directory logs: ./logs/ (per-directory)")
    
    # Error analysis
    if failed_directories > 0:
        log_master_message(f"")
        log_master_message(f"‚ùå Error Analysis:")
        log_master_message(f"  Failed directories: {failed_directories}")
        
        failed_details = [d for d in processing_details if not d['success']]
        if failed_details:
            log_master_message(f"  Failed directory details:")
            for detail in failed_details:
                dir_identifier = detail['directory_identifier']
                error_info = detail.get('error_message', 'Unknown error')
                log_master_message(f"    ‚Ä¢ {dir_identifier}: {error_info}")
                
                # Show detailed log path if available
                if detail.get('detailed_log_path'):
                    log_file = os.path.basename(detail['detailed_log_path'])
                    log_master_message(f"      Ì†ΩÌ≥ã Detailed log: {log_file}")
        
        log_master_message(f"  Check master log and detailed logs for complete error information")
    else:
        log_master_message(f"")
        log_master_message(f"Ì†ºÌæâ SUCCESS: All discovered directories processed successfully!")
    
    # Backup system information
    backup_dir = os.getenv('DOC_BACKUP_ABSOLUTE_PATH', 'Default (parent/doc_backups)')
    log_master_message(f"")
    log_master_message(f"Ì†ΩÌ≤æ Backup System:")
    log_master_message(f"  Backup directory: {backup_dir}")
    log_master_message(f"  All subdirectories use the same backup location")
    log_master_message(f"  Preserves original directory structure")
    
    log_master_message(f"")
    log_master_message(f"Ì†ΩÌ≥Ç Logs and Reports:")
    log_master_message(f"  Master processing log: ./logs/master_indexer.log")
    log_master_message(f"  Individual directory logs: ./logs/ (per-directory)")
    log_master_message(f"  Detailed indexer outputs: ./logs/indexer_detailed_*.log")
    log_master_message(f"  Backup location: {backup_dir}")
    log_master_message(f"{'='*80}")


def main():
    """
    Enhanced dynamic main function - discovers and processes Year/Number directory structure
    """
    print("Enhanced Dynamic Two-Level Master RAG Document Indexer Controller")
    print("=" * 80)
    print("Ì†ΩÌ¥ç ENHANCED DYNAMIC DISCOVERY APPROACH:")
    print("  ‚Ä¢ Dynamically discovers ANY year directories (2015, 2018, 2025, etc.)")
    print("  ‚Ä¢ Finds numbered subdirectories within each year")
    print("  ‚Ä¢ Excludes service directories (doc_backups, logs, etc.)")
    print("  ‚Ä¢ Calls indexer.py for each numbered subdirectory individually")
    print("  ‚Ä¢ ENHANCED: Captures detailed output and creates comprehensive logs")
    print("  ‚Ä¢ Processes: Year/Number structure whatever actually exists")
    print("=" * 80)
    
    # Load environment variables
    load_dotenv()
    
    # Get root directory from environment or use default
    root_directory = os.getenv("MASTER_DOCUMENTS_DIR", "./data/634")
    
    # Set backup directory for all subdirectories if not configured
    if not os.getenv("DOC_BACKUP_ABSOLUTE_PATH"):
        master_backup_dir = os.path.join(os.path.dirname(root_directory), "doc_backups")
        os.environ['DOC_BACKUP_ABSOLUTE_PATH'] = master_backup_dir
        print(f"Ì†ΩÌ≤æ Backup directory: {master_backup_dir}")
    else:
        print(f"Ì†ΩÌ≤æ Using configured backup directory: {os.getenv('DOC_BACKUP_ABSOLUTE_PATH')}")
    
    log_master_message(f"Enhanced Dynamic Master Indexer started")
    log_master_message(f"Root directory: {root_directory}")
    log_master_message(f"Backup directory: {os.getenv('DOC_BACKUP_ABSOLUTE_PATH', 'Not set')}")
    log_master_message(f"Service directories excluded: {', '.join(EXCLUDED_DIRECTORIES)}")
    log_master_message(f"Enhanced logging: Detailed output capture enabled")
    
    # Dynamically discover all processing directories
    all_processing_directories = discover_all_processing_directories(root_directory)
    
    if not all_processing_directories:
        log_master_message(f"ERROR: No valid numbered subdirectories found in {root_directory}")
        print("ERROR: No valid directories found to process")
        print("No Year/Number directory structure found or all directories were excluded")
        sys.exit(1)
    
    # Initialize counters
    total_directories = len(all_processing_directories)
    successful_directories = 0
    failed_directories = 0
    processing_details = []
    
    # Count unique years for summary
    year_directories_found = len(set(Path(d).parent for d in all_processing_directories))
    
    log_master_message(f"Starting enhanced dynamic processing of {total_directories} numbered directories")
    log_master_message(f"Spanning {year_directories_found} year directories")
    log_master_message(f"Enhanced logging will capture detailed output for each directory")
    
    master_start_time = time.time()
    
    # Process each discovered directory
    for index, directory_path in enumerate(all_processing_directories, 1):
        # Create readable directory identifier
        parts = Path(directory_path).parts
        if len(parts) >= 2:
            directory_identifier = f"{parts[-2]}/{parts[-1]}"
        else:
            directory_identifier = os.path.basename(directory_path)
        
        try:
            # Process directory using indexer.py with enhanced logging
            success, processing_time, error_message, detailed_log_path = process_single_directory(
                directory_path, index, total_directories
            )
            
            # Record processing details
            detail = {
                'directory_identifier': directory_identifier,
                'directory_path': directory_path,
                'success': success,
                'processing_time': processing_time,
                'error_message': error_message,
                'detailed_log_path': detailed_log_path
            }
            processing_details.append(detail)
            
            if success:
                successful_directories += 1
                log_master_message(f"‚úÖ Directory {directory_identifier} completed successfully")
            else:
                failed_directories += 1
                log_master_message(f"‚ùå Directory {directory_identifier} failed: {error_message}")
            
            # Enhanced progress update
            if index < total_directories:
                remaining = total_directories - index
                elapsed_time = time.time() - master_start_time
                avg_time_per_dir = elapsed_time / index
                estimated_remaining_time = remaining * avg_time_per_dir
                
                log_master_message(f"Ì†ΩÌ≥ä Progress: {index}/{total_directories} complete, {remaining} remaining")
                log_master_message(f"‚è±Ô∏è Estimated time remaining: {estimated_remaining_time/60:.1f} minutes")
           
        except KeyboardInterrupt:
            log_master_message(f"Ì†ΩÌªë INTERRUPTED: Enhanced dynamic master indexer interrupted by user")
            log_master_message(f"Processed {successful_directories} directories successfully before interruption")
            print("\nEnhanced dynamic master indexer interrupted by user")
            
            # Create partial summary
            total_time = time.time() - master_start_time
            create_final_summary(
                index, successful_directories, failed_directories, 
                total_time, processing_details, year_directories_found
            )
            sys.exit(1)
        
        except Exception as e:
            failed_directories += 1
            log_master_message(f"Ì†ΩÌ≤• FATAL ERROR processing {directory_identifier}: {e}")
            
            # Add error details
            error_detail = {
                'directory_identifier': directory_identifier,
                'directory_path': directory_path,
                'success': False,
                'processing_time': 0,
                'error_message': str(e),
                'detailed_log_path': None
            }
            processing_details.append(error_detail)
    
    # Calculate total time
    total_time = time.time() - master_start_time
    
    # Create enhanced final summary
    create_final_summary(
        total_directories, successful_directories, failed_directories, 
        total_time, processing_details, year_directories_found
    )
    
    # Enhanced console summary
    print(f"\nÌ†ºÌæâ Enhanced Dynamic Master Indexer Completed!")
    print(f"Ì†ΩÌ¥ç Discovery Results:")
    print(f"  Year directories found: {year_directories_found}")
    print(f"  Numbered directories found: {total_directories}")
    print(f"Ì†ΩÌ≥ä Processing Results:")
    print(f"  Successful: {successful_directories}")
    print(f"  Failed: {failed_directories}")
    print(f"  Total time: {total_time/60:.1f} minutes")
    
    print(f"Ì†ΩÌ≤æ Backup directory: {os.getenv('DOC_BACKUP_ABSOLUTE_PATH', 'Not configured')}")
    print(f"Ì†ΩÌ≥ã Master log: ./logs/master_indexer.log")
    print(f"Ì†ΩÌ≥Ñ Detailed logs: ./logs/indexer_detailed_*.log")
    
    # Show summary of detailed logs created
    try:
        log_files = [d.get('detailed_log_path') for d in processing_details if d.get('detailed_log_path')]
        if log_files:
            print(f"Ì†ΩÌ≥Ç {len(log_files)} detailed log files created:")
            for log_file in log_files[:5]:  # Show first 5
                print(f"     ‚Ä¢ {os.path.basename(log_file)}")
            if len(log_files) > 5:
                print(f"     ... and {len(log_files) - 5} more detailed logs")
    except Exception as e:
        log_master_message(f"Warning: Could not list detailed log files: {e}")
    
    # Exit with appropriate code
    if failed_directories > 0:
        print(f"‚ö†Ô∏è {failed_directories} directories failed - check logs for details")
        sys.exit(1)
    else:
        print(f"Ì†ºÌæâ All discovered directories processed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEnhanced dynamic master indexer interrupted by user")
        log_master_message("Enhanced dynamic master indexer interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR in enhanced dynamic master indexer: {e}")
        log_master_message(f"FATAL ERROR in enhanced dynamic master indexer: {e}")
        sys.exit(1)