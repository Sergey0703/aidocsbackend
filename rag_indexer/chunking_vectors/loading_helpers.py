#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified loading helpers module for RAG Document Indexer (Part 2: Chunking & Vectors Only)
Simple markdown loading and validation - no document conversion, OCR, or PDF processing
"""

import os
import time
from pathlib import Path
from datetime import datetime


def load_markdown_documents(config, progress_tracker):
    """
    Load markdown documents from directory (output from Docling Part 1)
    
    Args:
        config: Configuration object
        progress_tracker: Progress tracker instance
    
    Returns:
        tuple: (documents, loading_stats)
    """
    print(f"[*] Loading markdown documents from: {config.DOCUMENTS_DIR}")
    progress_tracker.add_checkpoint("Markdown loading started")
    
    # Print configuration summary
    print("\n[*] Loading Configuration:")
    print(f"   [*] Input directory: {config.DOCUMENTS_DIR}")
    print(f"   [*] Blacklisted directories: {', '.join(config.BLACKLIST_DIRECTORIES)}")
    print(f"   [*] Expected input: Markdown files from Docling (Part 1)")
    
    # Import markdown loader
    from .markdown_loader import create_markdown_loader
    
    # Create markdown loader
    print("\n📖 Initializing markdown loader...")
    loader = create_markdown_loader(
        documents_dir=config.DOCUMENTS_DIR,
        recursive=True,
        config=config
    )
    
    # Load markdown documents
    print("[*] Loading markdown files...")
    documents, loading_stats = loader.load_data()
    
    progress_tracker.add_checkpoint("Markdown documents loaded", len(documents))
    
    # Create processing summary
    processing_summary = {
        'documents_loaded': len(documents),
        'loading_stats': loading_stats,
        'total_documents': len(documents),
        'blacklist_applied': loading_stats.get('directories_skipped', 0) > 0,
        'blacklisted_directories': config.BLACKLIST_DIRECTORIES,
        'directories_scanned': loading_stats.get('directories_scanned', 0),
        'directories_skipped': loading_stats.get('directories_skipped', 0),
        'source_system': 'docling',
        'processing_stage': 'part_2_chunking_vectors'
    }
    
    return documents, processing_summary


def print_loading_summary(documents, processing_summary, loading_time):
    """
    Print loading summary for markdown documents
    
    Args:
        documents: List of loaded documents
        processing_summary: Processing summary dictionary
        loading_time: Time taken for loading
    """
    loading_stats = processing_summary.get('loading_stats', {})
    
    print(f"\n[*] MARKDOWN LOADING RESULTS:")
    print(f"[*] Loading time: {loading_time:.2f}s ({loading_time/60:.1f}m)")
    print(f"[*] Total documents loaded: {len(documents)}")
    
    if loading_stats:
        print(f"[*] Directories scanned: {loading_stats.get('directories_scanned', 0)}")
        
        if loading_stats.get('directories_skipped', 0) > 0:
            print(f"[*] Directories skipped: {loading_stats.get('directories_skipped', 0)}")
        
        print(f"[*] Markdown files found: {loading_stats.get('markdown_files', 0)}")
        print(f"[+] Successfully loaded: {loading_stats.get('documents_created', 0)}")
        print(f"[-] Failed to load: {loading_stats.get('failed_files', 0)}")
        
        if loading_stats.get('total_characters', 0) > 0:
            total_chars = loading_stats['total_characters']
            print(f"[*] Total characters: {total_chars:,}")
            
            if len(documents) > 0:
                avg_chars = total_chars / len(documents)
                print(f"[*] Average characters per document: {avg_chars:.0f}")
        
        # Show failed files if any
        if loading_stats.get('failed_files', 0) > 0:
            failed_list = loading_stats.get('failed_files_list', [])
            print(f"\n[!] Failed Files:")
            for i, failed_file in enumerate(failed_list[:5], 1):
                print(f"   {i}. {failed_file}")
            
            if len(failed_list) > 5:
                print(f"   ... and {len(failed_list) - 5} more")
    
    # Blacklist information
    if processing_summary.get('blacklist_applied', False):
        print(f"\n[*] Blacklist Filtering Applied:")
        blacklist_dirs = processing_summary.get('blacklisted_directories', [])
        print(f"   Excluded directories: {', '.join(blacklist_dirs)}")
    
    print(f"\n[+] Ready for chunking and embedding generation")


def validate_documents_for_processing(documents, config):
    """
    Validate documents have sufficient content for processing
    
    Args:
        documents: List of documents to validate
        config: Configuration object
    
    Returns:
        tuple: (documents_with_content, documents_without_content)
    """
    documents_with_content = []
    documents_without_content = []
    
    print("\n[*] Validating documents for processing...")
    
    min_length = config.MIN_CHUNK_LENGTH if config else 50
    
    for doc in documents:
        file_name = doc.metadata.get('file_name', 'Unknown File')
        text_content = doc.text.strip()
        
        # Validation checks
        if not text_content:
            documents_without_content.append(f"{file_name} - EMPTY (no text)")
        elif len(text_content) < min_length:
            documents_without_content.append(f"{file_name} - TOO SHORT ({len(text_content)} chars, min: {min_length})")
        elif len(text_content.split()) < 3:
            documents_without_content.append(f"{file_name} - TOO FEW WORDS ({len(text_content.split())} words)")
        else:
            documents_with_content.append(doc)
    
    return documents_with_content, documents_without_content


def print_document_validation_summary(documents_with_content, documents_without_content):
    """
    Print summary of document validation
    
    Args:
        documents_with_content: List of valid documents
        documents_without_content: List of invalid documents with reasons
    """
    total_documents = len(documents_with_content) + len(documents_without_content)
    
    print(f"\n[*] Document Validation Results:")
    print(f"   [*] Total documents: {total_documents}")
    print(f"   [+] Valid documents: {len(documents_with_content)}")
    print(f"   [-] Invalid documents: {len(documents_without_content)}")
    
    if total_documents > 0:
        validation_rate = (len(documents_with_content) / total_documents) * 100
        print(f"   [*] Validation success rate: {validation_rate:.1f}%")
    
    if documents_without_content:
        print(f"\n[!] Invalid Documents:")
        
        # Categorize by reason
        reasons = {}
        for doc_info in documents_without_content:
            if " - " in doc_info:
                reason = doc_info.split(" - ", 1)[1].split(" ")[0]
                reasons[reason] = reasons.get(reason, 0) + 1
        
        for reason, count in sorted(reasons.items()):
            print(f"   {reason}: {count} documents")
        
        # Show examples
        print(f"\n   Examples:")
        for i, doc_info in enumerate(documents_without_content[:5], 1):
            print(f"      {i}. {doc_info}")
        
        if len(documents_without_content) > 5:
            print(f"      ... and {len(documents_without_content) - 5} more")
        
        print(f"\n[*] Suggestions:")
        print(f"   - Check markdown files have readable content")
        print(f"   - Verify Docling (Part 1) processed files correctly")
        print(f"   - Consider adjusting MIN_CHUNK_LENGTH setting")
    
    if len(documents_with_content) > 0:
        print(f"\n[+] Proceeding with {len(documents_with_content)} valid documents")
    else:
        print(f"\n[-] No valid documents found for processing")


def check_processing_requirements(config):
    """
    Check if all requirements for processing are met
    
    Args:
        config: Configuration object
    
    Returns:
        tuple: (requirements_met, missing_requirements)
    """
    missing_requirements = []
    warnings = []
    
    print("\n[*] Checking Processing Requirements:")
    
    # Check database connection
    if not config.CONNECTION_STRING:
        missing_requirements.append("Database connection string")
        print(f"   [*] Database: [-] Connection string missing")
    else:
        print(f"   [*] Database: [+] Connection string configured")
    
    # Check Gemini API key
    if not config.GEMINI_API_KEY:
        missing_requirements.append("Gemini API key")
        print(f"   [*] Gemini API: [-] API key missing")
    else:
        print(f"   [*] Gemini API: [+] API key configured")
    
    # Check documents directory
    if not config.DOCUMENTS_DIR:
        missing_requirements.append("Documents directory path")
        print(f"   [*] Documents Dir: [-] Path not configured")
    elif not os.path.exists(config.DOCUMENTS_DIR):
        missing_requirements.append(f"Documents directory does not exist: {config.DOCUMENTS_DIR}")
        print(f"   [*] Documents Dir: [-] Does not exist: {config.DOCUMENTS_DIR}")
    else:
        # Check for markdown files
        from .markdown_loader import scan_markdown_files
        scan_results = scan_markdown_files(config.DOCUMENTS_DIR, recursive=True)
        
        # Filter out files from _metadata directory
        metadata_dir_name = '_metadata'
        actual_markdown_files = [
            f for f in scan_results.get('files', [])
            if metadata_dir_name not in Path(f['path']).parts
        ]
        actual_count = len(actual_markdown_files)
        
        if actual_count == 0:
            warnings.append(f"No markdown files found in {config.DOCUMENTS_DIR}")
            print(f"   [*] Documents Dir: [!] No markdown files found")
        else:
            print(f"   [*] Documents Dir: [+] {actual_count} markdown files found")
    
    # Check blacklist configuration
    if config.BLACKLIST_DIRECTORIES:
        print(f"   [*] Blacklist: [+] {len(config.BLACKLIST_DIRECTORIES)} directories excluded")
    else:
        warnings.append("No directories blacklisted - temp/log directories may be processed")
        print(f"   [*] Blacklist: [!] No directories excluded")
    
    # Print summary
    all_good = len(missing_requirements) == 0
    
    if all_good:
        print(f"\n[+] All processing requirements met!")
        if warnings:
            print(f"[!] Warnings: {len(warnings)}")
            for warning in warnings:
                print(f"   - {warning}")
    else:
        print(f"\n[-] Missing requirements: {len(missing_requirements)}")
        for requirement in missing_requirements:
            print(f"   - {requirement}")
        print(f"\nPlease fix missing requirements before proceeding.")
    
    return all_good, missing_requirements


def get_file_processing_summary(documents, processing_summary):
    """
    Get comprehensive file processing summary
    
    Args:
        documents: List of documents
        processing_summary: Processing summary dictionary
    
    Returns:
        dict: Comprehensive processing summary
    """
    loading_stats = processing_summary.get('loading_stats', {})
    
    summary = {
        'total_files_processed': len(documents),
        'processing_time': loading_stats.get('loading_time', 0),
        'source_system': processing_summary.get('source_system', 'docling'),
        'processing_stage': processing_summary.get('processing_stage', 'part_2'),
        'blacklist_applied': processing_summary.get('blacklist_applied', False),
        'directories_skipped': processing_summary.get('directories_skipped', 0),
        'markdown_files_found': loading_stats.get('markdown_files', 0),
        'documents_created': loading_stats.get('documents_created', 0),
        'failed_files': loading_stats.get('failed_files', 0),
        'total_characters': loading_stats.get('total_characters', 0),
        'processing_quality': 'unknown'
    }
    
    # Determine processing quality
    total_attempted = summary['markdown_files_found']
    if total_attempted == 0:
        summary['processing_quality'] = 'no_files'
    else:
        success_rate = (summary['documents_created'] / total_attempted) * 100
        
        if success_rate >= 95:
            summary['processing_quality'] = 'excellent'
        elif success_rate >= 80:
            summary['processing_quality'] = 'good'
        elif success_rate >= 50:
            summary['processing_quality'] = 'acceptable'
        else:
            summary['processing_quality'] = 'poor'
    
    return summary


def get_loading_recommendations(processing_summary, config):
    """
    Get recommendations for improving loading performance
    
    Args:
        processing_summary: Processing summary dictionary
        config: Configuration object
    
    Returns:
        list: List of recommendations
    """
    recommendations = []
    loading_stats = processing_summary.get('loading_stats', {})
    
    # Check success rate
    markdown_files = loading_stats.get('markdown_files', 0)
    documents_created = loading_stats.get('documents_created', 0)
    
    if markdown_files > 0:
        success_rate = (documents_created / markdown_files) * 100
        
        if success_rate < 80:
            recommendations.append(
                f"Low loading success rate ({success_rate:.1f}%). "
                "Check Docling (Part 1) output quality and markdown file validity."
            )
    
    # Check failed files
    failed_files = loading_stats.get('failed_files', 0)
    if failed_files > 0:
        recommendations.append(
            f"{failed_files} files failed to load. "
            "Review failed file list and verify markdown format."
        )
    
    # Check blacklist usage
    if not processing_summary.get('blacklist_applied', False):
        recommendations.append(
            "Consider enabling blacklist filtering to exclude temp/log directories."
        )
    
    # Check total characters
    total_chars = loading_stats.get('total_characters', 0)
    if total_chars > 0 and documents_created > 0:
        avg_chars = total_chars / documents_created
        
        if avg_chars < 100:
            recommendations.append(
                f"Very short documents detected (avg: {avg_chars:.0f} chars). "
                "Verify Docling is extracting content properly."
            )
    
    # Performance recommendations
    if markdown_files > 1000:
        recommendations.append(
            "Large number of files detected. Consider increasing PROCESSING_BATCH_SIZE for better performance."
        )
    
    if not recommendations:
        recommendations.append("Current loading configuration appears optimal.")
    
    return recommendations


def print_loading_recommendations(recommendations):
    """
    Print loading recommendations
    
    Args:
        recommendations: List of recommendations
    """
    if not recommendations:
        return
    
    print(f"\n[*] LOADING RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")


def create_comprehensive_loading_report(documents, processing_summary, loading_time, config):
    """
    Create comprehensive loading report
    
    Args:
        documents: List of documents
        processing_summary: Processing summary dictionary
        loading_time: Total loading time
        config: Configuration object
    
    Returns:
        dict: Comprehensive loading report
    """
    file_summary = get_file_processing_summary(documents, processing_summary)
    file_summary['processing_time'] = loading_time
    
    recommendations = get_loading_recommendations(processing_summary, config)
    
    comprehensive_report = {
        'timestamp': datetime.now().isoformat(),
        'file_summary': file_summary,
        'recommendations': recommendations,
        'configuration_used': {
            'documents_dir': config.DOCUMENTS_DIR,
            'blacklist_directories': config.BLACKLIST_DIRECTORIES,
            'chunk_size': config.CHUNK_SIZE,
            'batch_size': config.PROCESSING_BATCH_SIZE,
            'min_chunk_length': config.MIN_CHUNK_LENGTH
        },
        'processing_summary': processing_summary
    }
    
    return comprehensive_report


if __name__ == "__main__":
    print("📖 Simplified Loading Helpers Module")
    print("Purpose: Load markdown files from Docling (Part 1) output")
    print("=" * 60)