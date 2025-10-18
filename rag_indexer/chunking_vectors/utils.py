#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions module for RAG Document Indexer
Contains helper functions, formatters, and common utilities with enhanced failed files logging
"""

import os
import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path


def save_failed_files_details(failed_files_list, log_dir="./logs"):
    """
    Save complete list of failed files to dedicated log (append mode)
    
    Args:
        failed_files_list: List of failed files with details
        log_dir: Directory for log files
    
    Returns:
        str: Path to log file if successful, None otherwise
    """
    if not failed_files_list:
        return None
    
    # Ensure log directory exists
    if not ensure_directory_exists(log_dir):
        print(f"WARNING: Could not create log directory {log_dir}")
        return None
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = os.path.join(log_dir, "failed_files_details.log")
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:  # ??????????: 'a' ?????? 'w' ??? ???????????
            f.write(f"\n{'='*60}\n")
            f.write(f"FAILED FILES REPORT - {timestamp}\n")
            f.write(f"{'='*60}\n")
            f.write(f"Total failed files: {len(failed_files_list)}\n")
            f.write(f"{'*'*60}\n\n")
            
            for i, failed_file in enumerate(failed_files_list, 1):
                f.write(f"{i:3d}. {failed_file}\n")
            
            f.write(f"\n{'*'*60}\n")
            f.write(f"End of report - {len(failed_files_list)} files listed\n")
            f.write(f"{'='*60}\n\n")
        
        return log_file
        
    except Exception as e:
        print(f"WARNING: Could not save failed files details: {e}")
        return None


def format_time(seconds):
    """
    Format seconds into human-readable time string
    
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
    Format bytes into human-readable size string
    
    Args:
        bytes_size: Size in bytes
    
    Returns:
        str: Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}PB"


def format_number(number):
    """
    Format number with thousands separators
    
    Args:
        number: Number to format
    
    Returns:
        str: Formatted number string
    """
    return f"{number:,}"


def calculate_eta(processed, total, elapsed_time):
    """
    Calculate estimated time of arrival
    
    Args:
        processed: Number of items processed
        total: Total number of items
        elapsed_time: Time elapsed so far
    
    Returns:
        tuple: (eta_seconds, finish_time_str)
    """
    if processed == 0 or elapsed_time == 0:
        return 0, "Unknown"
    
    rate = processed / elapsed_time
    remaining = total - processed
    eta_seconds = remaining / rate if rate > 0 else 0
    
    finish_time = datetime.now() + timedelta(seconds=eta_seconds)
    finish_time_str = finish_time.strftime('%H:%M')
    
    return eta_seconds, finish_time_str


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


def safe_file_write(file_path, content, encoding='utf-8'):
    """
    Safely write content to file with error handling
    
    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory and not ensure_directory_exists(directory):
            return False
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"ERROR: Could not write to {file_path}: {e}")
        return False


def safe_file_append(file_path, content, encoding='utf-8'):
    """
    Safely append content to file with error handling
    
    Args:
        file_path: Path to file
        content: Content to append
        encoding: File encoding
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory and not ensure_directory_exists(directory):
            return False
        
        with open(file_path, 'a', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"ERROR: Could not append to {file_path}: {e}")
        return False


def cleanup_log_files(max_age_days=30, log_directory="./"):
    """
    Clean up old log files
    
    Args:
        max_age_days: Maximum age of log files in days
        log_directory: Directory containing log files
    
    Returns:
        int: Number of files cleaned up
    """
    try:
        log_extensions = ['.log', '.txt']
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        cleaned_count = 0
        
        for file_path in Path(log_directory).glob('*'):
            if file_path.is_file() and file_path.suffix in log_extensions:
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        print(f"Cleaned up old log file: {file_path.name}")
                    except Exception as e:
                        print(f"WARNING: Could not delete {file_path}: {e}")
        
        return cleaned_count
    except Exception as e:
        print(f"ERROR: Error during log cleanup: {e}")
        return 0


class InterruptHandler:
    """Handler for graceful interruption (Ctrl+C)"""
    
    def __init__(self):
        self.interrupted = False
        self.original_handler = None
    
    def __enter__(self):
        self.original_handler = signal.signal(signal.SIGINT, self._handle_interrupt)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.signal(signal.SIGINT, self.original_handler)
    
    def _handle_interrupt(self, signum, frame):
        self.interrupted = True
        print("\n\nWARNING: Interrupt signal received (Ctrl+C)")
        print("INFO: Finishing current operation safely...")
        print("INFO: Press Ctrl+C again to force exit")
        
        # Set up handler for second interrupt
        signal.signal(signal.SIGINT, self._force_exit)
    
    def _force_exit(self, signum, frame):
        print("\nERROR: Force exit requested")
        sys.exit(1)
    
    def check_interrupted(self):
        """Check if interrupt was received"""
        return self.interrupted


class PerformanceMonitor:
    """Monitor performance metrics during processing"""
    
    def __init__(self):
        self.metrics = {
            'start_time': None,
            'checkpoints': [],
            'peak_memory': 0,
            'total_operations': 0
        }
    
    def start(self):
        """Start performance monitoring"""
        self.metrics['start_time'] = time.time()
        self.metrics['checkpoints'] = []
    
    def checkpoint(self, name, operations_count=0):
        """
        Add a performance checkpoint
        
        Args:
            name: Name of the checkpoint
            operations_count: Number of operations completed
        """
        if self.metrics['start_time'] is None:
            self.start()
        
        current_time = time.time()
        elapsed = current_time - self.metrics['start_time']
        
        checkpoint = {
            'name': name,
            'timestamp': current_time,
            'elapsed': elapsed,
            'operations': operations_count,
            'rate': operations_count / elapsed if elapsed > 0 else 0
        }
        
        self.metrics['checkpoints'].append(checkpoint)
        self.metrics['total_operations'] = max(self.metrics['total_operations'], operations_count)
    
    def get_current_rate(self):
        """Get current processing rate"""
        if not self.metrics['checkpoints']:
            return 0
        
        latest = self.metrics['checkpoints'][-1]
        return latest['rate']
    
    def get_average_rate(self):
        """Get average processing rate"""
        if not self.metrics['checkpoints'] or self.metrics['start_time'] is None:
            return 0
        
        total_elapsed = time.time() - self.metrics['start_time']
        return self.metrics['total_operations'] / total_elapsed if total_elapsed > 0 else 0
    
    def print_performance_summary(self):
        """Print performance summary"""
        if not self.metrics['checkpoints']:
            print("No performance data available")
            return
        
        total_elapsed = time.time() - self.metrics['start_time']
        avg_rate = self.get_average_rate()
        
        print(f"\nPerformance Summary:")
        print(f"  Total time: {format_time(total_elapsed)}")
        print(f"  Total operations: {format_number(self.metrics['total_operations'])}")
        print(f"  Average rate: {avg_rate:.2f} ops/sec")
        
        if len(self.metrics['checkpoints']) > 1:
            print(f"  Recent checkpoints:")
            for checkpoint in self.metrics['checkpoints'][-3:]:
                print(f"    {checkpoint['name']}: {checkpoint['rate']:.2f} ops/sec")


class StatusReporter:
    """Report status and progress in a structured way"""
    
    def __init__(self, title="Processing Status"):
        self.title = title
        self.sections = []
    
    def add_section(self, title, items):
        """
        Add a section to the report
        
        Args:
            title: Section title
            items: List of items or dict of key-value pairs
        """
        self.sections.append({
            'title': title,
            'items': items
        })
    
    def print_report(self):
        """Print the complete status report"""
        print(f"\n{'=' * 60}")
        print(f"{self.title}")
        print(f"{'=' * 60}")
        
        for section in self.sections:
            print(f"\n{section['title']}:")
            
            if isinstance(section['items'], dict):
                for key, value in section['items'].items():
                    print(f"  {key}: {value}")
            elif isinstance(section['items'], list):
                for item in section['items']:
                    print(f"  - {item}")
            else:
                print(f"  {section['items']}")
        
        print(f"\n{'=' * 60}")
    
    def clear(self):
        """Clear all sections"""
        self.sections = []


def validate_python_version(min_version=(3, 8)):
    """
    Validate Python version meets minimum requirements
    
    Args:
        min_version: Minimum required version tuple
    
    Returns:
        bool: True if version is adequate
    """
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        print(f"ERROR: Python {min_version[0]}.{min_version[1]}+ required")
        print(f"Current version: {current_version[0]}.{current_version[1]}")
        return False
    
    return True


def check_disk_space(path, min_free_gb=1):
    """
    Check available disk space
    
    Args:
        path: Path to check
        min_free_gb: Minimum free space in GB
    
    Returns:
        tuple: (has_space, available_gb)
    """
    try:
        stat = os.statvfs(path)
        available_bytes = stat.f_bavail * stat.f_frsize
        available_gb = available_bytes / (1024**3)
        
        return available_gb >= min_free_gb, available_gb
    except Exception as e:
        print(f"WARNING: Could not check disk space: {e}")
        return True, 0  # Assume enough space if check fails


def check_memory_usage():
    """
    Check current memory usage (if psutil is available)
    
    Returns:
        dict: Memory information or None if not available
    """
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_percent': memory.percent,
            'available_percent': (memory.available / memory.total) * 100
        }
    except ImportError:
        return None
    except Exception as e:
        print(f"WARNING: Could not check memory usage: {e}")
        return None


def print_system_info():
    """Print system information"""
    print("System Information:")
    print(f"  Python version: {sys.version.split()[0]}")
    print(f"  Platform: {sys.platform}")
    
    # Memory info
    memory_info = check_memory_usage()
    if memory_info:
        print(f"  Total RAM: {memory_info['total_gb']:.1f}GB")
        print(f"  Available RAM: {memory_info['available_gb']:.1f}GB ({memory_info['available_percent']:.1f}%)")
    else:
        print("  Memory info: Not available (psutil not installed)")
    
    # Disk space
    has_space, available_gb = check_disk_space("./")
    print(f"  Available disk space: {available_gb:.1f}GB")
    
    if not has_space:
        print("  WARNING: Low disk space!")


def create_run_summary(start_time, end_time, stats, failed_files_list=None):
    """
    Create a summary of the processing run
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        stats: Processing statistics dict
        failed_files_list: List of failed files (optional)
    
    Returns:
        str: Formatted summary
    """
    duration = end_time - start_time
    
    summary = []
    summary.append(f"Processing Run Summary")
    summary.append(f"=" * 50)
    summary.append(f"Start time: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"End time: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"Duration: {format_time(duration)}")
    summary.append("")
    
    # Main statistics
    for key, value in stats.items():
        if isinstance(value, float):
            summary.append(f"{key}: {value:.2f}")
        elif isinstance(value, int):
            summary.append(f"{key}: {format_number(value)}")
        else:
            summary.append(f"{key}: {value}")
    
    # Failed files summary - ??????????: ?????????? ??????
    summary.append("")
    summary.append("FAILED FILES SUMMARY:")
    summary.append("-" * 30)
    
    # ??????????: ????????? ? ??????, ? ??? ?????
    if failed_files_list is None or len(failed_files_list) == 0:
        summary.append("? No failed files")
    else:
        summary.append(f"? Total failed files: {len(failed_files_list)}")
        summary.append(f"?? Details saved to: /logs/failed_files_details.log")
        
        # Show first 5 for quick reference
        if len(failed_files_list) <= 5:
            summary.append("")
            summary.append("All failed files:")
            for i, failed_file in enumerate(failed_files_list, 1):
                summary.append(f"  {i}. {failed_file}")
        else:
            summary.append("")
            summary.append("First 5 failed files:")
            for i, failed_file in enumerate(failed_files_list[:5], 1):
                summary.append(f"  {i}. {failed_file}")
            summary.append(f"  ... and {len(failed_files_list) - 5} more (see detailed log)")
    
    summary.append("")
    summary.append("=" * 50)
    
    return "\n".join(summary)


def setup_logging_directory():
    """Setup logging directory and clean old logs"""
    log_dir = "./logs"
    
    if ensure_directory_exists(log_dir):
        # Clean up old logs
        cleaned = cleanup_log_files(max_age_days=30, log_directory=log_dir)
        if cleaned > 0:
            print(f"Cleaned up {cleaned} old log files")
        return log_dir
    else:
        print("WARNING: Could not create logs directory, using current directory")
        return "./"