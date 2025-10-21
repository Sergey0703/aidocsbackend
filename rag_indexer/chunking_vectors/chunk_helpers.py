#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chunk helpers module for RAG Document Indexer
Contains helper functions for chunk creation, filtering, and processing
UPDATED: Now supports both SentenceSplitter and Docling HybridChunker
"""

import time
import logging
from .embedding_processor import create_node_processor

logger = logging.getLogger(__name__)


def create_and_filter_chunks_enhanced(documents, config, node_parser, progress_tracker):
    """
    Enhanced chunk creation and filtering with quality analysis
    UPDATED: Now supports both SentenceSplitter and HybridChunker

    Args:
        documents: List of documents
        config: Enhanced configuration object
        node_parser: Node parser instance (SentenceSplitter)
        progress_tracker: Progress tracker instance

    Returns:
        tuple: (valid_nodes, invalid_nodes, enhanced_node_stats)
    """
    print("\n🧩 Enhanced chunk creation and quality analysis...")
    chunk_start_time = time.time()

    # Check if hybrid chunking is enabled
    hybrid_settings = config.get_hybrid_chunking_settings() if hasattr(config, 'get_hybrid_chunking_settings') else {'enabled': False}
    use_hybrid = hybrid_settings.get('enabled', False)

    try:
        if use_hybrid:
            # Hybrid chunking path (Docling HybridChunker)
            print("   Using Hybrid Chunking (Docling HybridChunker)")
            logger.info("🧩 Using Hybrid Chunking (Docling HybridChunker)")

            try:
                from .hybrid_chunker import create_hybrid_chunker, is_hybrid_chunking_available

                if not is_hybrid_chunking_available():
                    print("   ❌ Hybrid chunking not available! Falling back to SentenceSplitter.")
                    print("      Install with: pip install 'docling-core[chunking]' transformers")
                    logger.error("❌ Hybrid chunking requested but not available! Falling back to SentenceSplitter.")
                    use_hybrid = False
                else:
                    # Create hybrid chunker and chunk documents
                    chunker = create_hybrid_chunker(config)
                    all_nodes = chunker.chunk_documents(documents)
                    print(f"   ✅ Hybrid chunking created {len(all_nodes)} chunks from {len(documents)} documents")
                    logger.info(f"   ✅ Hybrid chunking created {len(all_nodes)} chunks from {len(documents)} documents")

            except Exception as e:
                print(f"   ❌ Hybrid chunking failed: {e}")
                print("      Falling back to SentenceSplitter")
                logger.error(f"❌ Hybrid chunking failed: {e}")
                logger.error("   Falling back to SentenceSplitter")
                use_hybrid = False

        if not use_hybrid:
            # Legacy path: SentenceSplitter
            print("   Using Legacy Chunking (SentenceSplitter)")
            logger.info("🧩 Using Legacy Chunking (SentenceSplitter)")

            # Create nodes with enhanced metadata
            all_nodes = node_parser.get_nodes_from_documents(documents, show_progress=True)
            print(f"   ✅ SentenceSplitter created {len(all_nodes)} chunks from {len(documents)} documents")
            logger.info(f"   ✅ SentenceSplitter created {len(all_nodes)} chunks from {len(documents)} documents")

        progress_tracker.add_checkpoint("Enhanced chunks created", len(all_nodes))

    except Exception as e:
        print(f"❌ Failed to parse documents into chunks: {e}")
        logger.error(f"Failed to parse documents into chunks: {e}")
        raise
    
    chunk_time = time.time() - chunk_start_time
    print(f"✅ Document chunking completed in {chunk_time:.2f}s")
    
    # Enhanced node processing with quality analysis
    chunk_settings = config.get_chunk_settings()
    node_processor = create_node_processor(chunk_settings['min_chunk_length'])
    
    print("🔍 Applying enhanced quality filters...")
    filter_start_time = time.time()
    
    valid_nodes, invalid_nodes = node_processor.filter_and_enhance_nodes(all_nodes, show_progress=True)
    
    filter_time = time.time() - filter_start_time
    print(f"✅ Quality filtering completed in {filter_time:.2f}s")
    
    # Enhanced statistics
    enhanced_node_stats = node_processor.get_node_statistics(valid_nodes)
    
    # Add filtering statistics
    enhanced_node_stats.update({
        'total_nodes_created': len(all_nodes),
        'valid_nodes': len(valid_nodes),
        'invalid_nodes': len(invalid_nodes),
        'filter_success_rate': (len(valid_nodes) / len(all_nodes) * 100) if len(all_nodes) > 0 else 0,
        'chunk_creation_time': chunk_time,
        'filter_processing_time': filter_time,
        'total_processing_time': chunk_time + filter_time
    })
    
    progress_tracker.add_checkpoint("Enhanced chunks filtered", len(valid_nodes))
    
    # Print enhanced chunk statistics
    print_enhanced_chunk_statistics(enhanced_node_stats, invalid_nodes)
    
    return valid_nodes, invalid_nodes, enhanced_node_stats


def print_enhanced_chunk_statistics(node_stats, invalid_nodes):
    """
    Print comprehensive chunk statistics

    Args:
        node_stats: Enhanced node statistics
        invalid_nodes: List of invalid nodes with reasons
    """
    print(f"\n📊 ENHANCED CHUNK STATISTICS:")
    print(f"📝 Total chunks created: {node_stats.get('total_nodes_created', 0):,}")
    print(f"✅ Valid chunks: {node_stats.get('valid_nodes', 0):,}")
    print(f"❌ Invalid chunks filtered: {node_stats.get('invalid_nodes', 0):,}")
    print(f"📈 Filter success rate: {node_stats.get('filter_success_rate', 0):.1f}%")

    # Only print quality metrics if there are valid chunks
    if node_stats.get('valid_nodes', 0) > 0:
        print(f"\n🎯 Quality Metrics:")
        print(f"   Average content length: {node_stats.get('avg_content_length', 0):.0f} characters")
        print(f"   Length range: {node_stats.get('min_content_length', 0)}-{node_stats.get('max_content_length', 0)}")
        print(f"   Average words per chunk: {node_stats.get('avg_word_count', 0):.1f}")
        print(f"   Word count range: {node_stats.get('min_word_count', 0)}-{node_stats.get('max_word_count', 0)}")

        print(f"\n📁 File Distribution:")
        print(f"   Unique files processed: {node_stats.get('unique_files', 0):,}")
        print(f"   Average chunks per file: {node_stats.get('chunks_per_file', 0):.1f}")
    else:
        print(f"\n⚠️ No valid chunks created - cannot compute quality metrics")

    print(f"\n⚡ Processing Performance:")
    print(f"   Chunk creation time: {node_stats.get('chunk_creation_time', 0):.2f}s")
    print(f"   Quality filtering time: {node_stats.get('filter_processing_time', 0):.2f}s")
    print(f"   Total processing time: {node_stats.get('total_processing_time', 0):.2f}s")
    
    # Show sample of invalid chunk reasons
    if invalid_nodes:
        invalid_reasons = {}
        for invalid_node in invalid_nodes[:50]:  # Sample first 50
            reason = invalid_node.get('reason', 'unknown')
            invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
        
        print(f"\n🔍 Invalid Chunk Analysis (sample):")
        for reason, count in sorted(invalid_reasons.items()):
            print(f"   {reason.replace('_', ' ').title()}: {count}")


def analyze_chunk_quality(valid_nodes, invalid_nodes):
    """
    Analyze chunk quality metrics
    
    Args:
        valid_nodes: List of valid nodes
        invalid_nodes: List of invalid nodes with reasons
    
    Returns:
        dict: Quality analysis results
    """
    total_nodes = len(valid_nodes) + len(invalid_nodes)
    
    if total_nodes == 0:
        return {'error': 'No nodes to analyze'}
    
    # Basic quality metrics
    quality_metrics = {
        'total_chunks': total_nodes,
        'valid_chunks': len(valid_nodes),
        'invalid_chunks': len(invalid_nodes),
        'success_rate': (len(valid_nodes) / total_nodes * 100),
        'failure_rate': (len(invalid_nodes) / total_nodes * 100)
    }
    
    # Analyze valid chunks
    if valid_nodes:
        content_lengths = [len(node.get_content()) for node in valid_nodes]
        word_counts = [len(node.get_content().split()) for node in valid_nodes]
        
        quality_metrics.update({
            'avg_content_length': sum(content_lengths) / len(content_lengths),
            'min_content_length': min(content_lengths),
            'max_content_length': max(content_lengths),
            'avg_word_count': sum(word_counts) / len(word_counts),
            'min_word_count': min(word_counts),
            'max_word_count': max(word_counts)
        })
    
    # Analyze failure reasons
    if invalid_nodes:
        failure_reasons = {}
        for invalid_node in invalid_nodes:
            reason = invalid_node.get('reason', 'unknown')
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # Sort by frequency
        sorted_reasons = sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)
        quality_metrics['failure_reasons'] = dict(sorted_reasons)
        quality_metrics['most_common_failure'] = sorted_reasons[0] if sorted_reasons else ('none', 0)
    
    return quality_metrics


def get_chunk_distribution_stats(valid_nodes):
    """
    Get statistics about chunk distribution across files
    
    Args:
        valid_nodes: List of valid nodes
    
    Returns:
        dict: Distribution statistics
    """
    if not valid_nodes:
        return {'error': 'No valid nodes to analyze'}
    
    # Group chunks by file
    file_chunks = {}
    for node in valid_nodes:
        file_name = node.metadata.get('file_name', 'Unknown')
        if file_name not in file_chunks:
            file_chunks[file_name] = []
        file_chunks[file_name].append(node)
    
    # Calculate distribution statistics
    chunks_per_file = [len(chunks) for chunks in file_chunks.values()]
    
    distribution_stats = {
        'unique_files': len(file_chunks),
        'total_chunks': len(valid_nodes),
        'avg_chunks_per_file': sum(chunks_per_file) / len(chunks_per_file),
        'min_chunks_per_file': min(chunks_per_file),
        'max_chunks_per_file': max(chunks_per_file),
    }
    
    # Find files with extreme chunk counts
    sorted_files = sorted(file_chunks.items(), key=lambda x: len(x[1]), reverse=True)
    
    distribution_stats.update({
        'files_with_most_chunks': [(name, len(chunks)) for name, chunks in sorted_files[:5]],
        'files_with_least_chunks': [(name, len(chunks)) for name, chunks in sorted_files[-5:]],
    })
    
    # Calculate chunk size distribution
    content_lengths = [len(node.get_content()) for node in valid_nodes]
    content_lengths.sort()
    
    n = len(content_lengths)
    distribution_stats.update({
        'content_length_median': content_lengths[n//2] if n > 0 else 0,
        'content_length_25th_percentile': content_lengths[n//4] if n > 3 else 0,
        'content_length_75th_percentile': content_lengths[3*n//4] if n > 3 else 0,
    })
    
    return distribution_stats


def validate_chunk_content(valid_nodes, config):
    """
    Validate chunk content for potential issues
    
    Args:
        valid_nodes: List of valid nodes
        config: Configuration object
    
    Returns:
        dict: Validation results
    """
    validation_results = {
        'total_validated': len(valid_nodes),
        'issues_found': 0,
        'warnings': [],
        'potential_problems': []
    }
    
    if not valid_nodes:
        return validation_results
    
    # Check for potential encoding issues
    encoding_issues = 0
    for node in valid_nodes:
        content = node.get_content()
        
        # Look for common encoding issue indicators
        if '�' in content or '\x00' in content:
            encoding_issues += 1
    
    if encoding_issues > 0:
        validation_results['warnings'].append(f"Found {encoding_issues} chunks with potential encoding issues")
        validation_results['issues_found'] += encoding_issues
    
    # Check for extremely short chunks (might indicate processing issues)
    min_reasonable_length = config.MIN_CHUNK_LENGTH * 2  # Double the minimum as reasonable
    short_chunks = sum(1 for node in valid_nodes if len(node.get_content()) < min_reasonable_length)
    
    if short_chunks > len(valid_nodes) * 0.1:  # More than 10% are very short
        validation_results['warnings'].append(f"Found {short_chunks} very short chunks (< {min_reasonable_length} chars)")
        validation_results['potential_problems'].append('many_short_chunks')
    
    # Check for extremely long chunks (might indicate chunking issues)
    max_reasonable_length = config.CHUNK_SIZE * 3  # Triple the chunk size as concerning
    long_chunks = sum(1 for node in valid_nodes if len(node.get_content()) > max_reasonable_length)
    
    if long_chunks > 0:
        validation_results['warnings'].append(f"Found {long_chunks} unexpectedly long chunks (> {max_reasonable_length} chars)")
        validation_results['potential_problems'].append('some_oversized_chunks')
    
    # Check for duplicate content
    content_hashes = {}
    duplicate_chunks = 0
    
    for node in valid_nodes:
        content_hash = hash(node.get_content())
        if content_hash in content_hashes:
            duplicate_chunks += 1
        else:
            content_hashes[content_hash] = 1
    
    if duplicate_chunks > 0:
        validation_results['warnings'].append(f"Found {duplicate_chunks} potentially duplicate chunks")
        validation_results['potential_problems'].append('duplicate_content')
    
    # Check metadata completeness
    missing_metadata = 0
    for node in valid_nodes:
        required_fields = ['file_name', 'file_path']
        if not all(field in node.metadata for field in required_fields):
            missing_metadata += 1
    
    if missing_metadata > 0:
        validation_results['warnings'].append(f"Found {missing_metadata} chunks with incomplete metadata")
        validation_results['potential_problems'].append('incomplete_metadata')
    
    return validation_results


def optimize_chunk_processing_settings(chunk_stats, config):
    """
    Suggest optimizations based on chunk processing statistics
    
    Args:
        chunk_stats: Chunk processing statistics
        config: Current configuration
    
    Returns:
        dict: Optimization suggestions
    """
    suggestions = {
        'current_performance': {},
        'optimization_suggestions': [],
        'configuration_recommendations': {}
    }
    
    # Analyze current performance
    suggestions['current_performance'] = {
        'chunk_creation_speed': chunk_stats.get('total_nodes_created', 0) / chunk_stats.get('chunk_creation_time', 1),
        'filter_success_rate': chunk_stats.get('filter_success_rate', 0),
        'avg_chunk_size': chunk_stats.get('avg_content_length', 0),
        'processing_efficiency': chunk_stats.get('valid_nodes', 0) / chunk_stats.get('total_processing_time', 1)
    }
    
    # Chunk size optimization
    avg_length = chunk_stats.get('avg_content_length', 0)
    if avg_length < config.CHUNK_SIZE * 0.5:
        suggestions['optimization_suggestions'].append(
            f"Consider reducing CHUNK_SIZE from {config.CHUNK_SIZE} to {int(avg_length * 1.5)} for better efficiency"
        )
        suggestions['configuration_recommendations']['CHUNK_SIZE'] = int(avg_length * 1.5)
    elif avg_length > config.CHUNK_SIZE * 1.5:
        suggestions['optimization_suggestions'].append(
            f"Consider increasing CHUNK_SIZE from {config.CHUNK_SIZE} to {int(avg_length * 0.8)} for more content per chunk"
        )
        suggestions['configuration_recommendations']['CHUNK_SIZE'] = int(avg_length * 0.8)
    
    # Filter success rate optimization
    filter_rate = chunk_stats.get('filter_success_rate', 100)
    if filter_rate < 80:
        suggestions['optimization_suggestions'].append(
            f"Low filter success rate ({filter_rate:.1f}%). Consider adjusting MIN_CHUNK_LENGTH or content preprocessing"
        )
        suggestions['configuration_recommendations']['MIN_CHUNK_LENGTH'] = max(50, config.MIN_CHUNK_LENGTH // 2)
    
    # Processing time optimization
    total_time = chunk_stats.get('total_processing_time', 0)
    creation_time = chunk_stats.get('chunk_creation_time', 0)
    filter_time = chunk_stats.get('filter_processing_time', 0)
    
    if filter_time > creation_time * 2:
        suggestions['optimization_suggestions'].append(
            "Filtering takes much longer than chunk creation. Consider optimizing filter logic or reducing filter strictness"
        )
    
    # Chunk distribution optimization
    chunks_per_file = chunk_stats.get('chunks_per_file', 0)
    if chunks_per_file < 2:
        suggestions['optimization_suggestions'].append(
            "Very few chunks per file. Consider reducing CHUNK_SIZE or MIN_CHUNK_LENGTH for better granularity"
        )
    elif chunks_per_file > 50:
        suggestions['optimization_suggestions'].append(
            "Very many chunks per file. Consider increasing CHUNK_SIZE for better processing efficiency"
        )
    
    return suggestions


def print_chunk_optimization_suggestions(optimization_results):
    """
    Print chunk processing optimization suggestions
    
    Args:
        optimization_results: Results from optimize_chunk_processing_settings
    """
    print(f"\n🔧 CHUNK PROCESSING OPTIMIZATION ANALYSIS:")
    
    # Current performance
    perf = optimization_results['current_performance']
    print(f"📊 Current Performance:")
    print(f"   Chunk creation speed: {perf.get('chunk_creation_speed', 0):.1f} chunks/sec")
    print(f"   Filter success rate: {perf.get('filter_success_rate', 0):.1f}%")
    print(f"   Average chunk size: {perf.get('avg_chunk_size', 0):.0f} characters")
    print(f"   Processing efficiency: {perf.get('processing_efficiency', 0):.1f} valid chunks/sec")
    
    # Optimization suggestions
    suggestions = optimization_results['optimization_suggestions']
    if suggestions:
        print(f"\n💡 Optimization Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
    else:
        print(f"\n✅ Current chunk processing settings appear optimal")
    
    # Configuration recommendations
    recommendations = optimization_results['configuration_recommendations']
    if recommendations:
        print(f"\n⚙️ Recommended Configuration Changes:")
        for key, value in recommendations.items():
            print(f"   {key}={value}")
    
    print()


def create_chunk_processing_report(valid_nodes, invalid_nodes, chunk_stats, config):
    """
    Create comprehensive chunk processing report
    
    Args:
        valid_nodes: List of valid nodes
        invalid_nodes: List of invalid nodes
        chunk_stats: Chunk processing statistics
        config: Configuration object
    
    Returns:
        dict: Comprehensive processing report
    """
    report = {
        'timestamp': time.time(),
        'summary': {
            'total_chunks_created': len(valid_nodes) + len(invalid_nodes),
            'valid_chunks': len(valid_nodes),
            'invalid_chunks': len(invalid_nodes),
            'success_rate': chunk_stats.get('filter_success_rate', 0),
            'processing_time': chunk_stats.get('total_processing_time', 0)
        }
    }
    
    # Quality analysis
    report['quality_analysis'] = analyze_chunk_quality(valid_nodes, invalid_nodes)
    
    # Distribution statistics
    report['distribution_stats'] = get_chunk_distribution_stats(valid_nodes)
    
    # Content validation
    report['validation_results'] = validate_chunk_content(valid_nodes, config)
    
    # Optimization suggestions
    report['optimization_suggestions'] = optimize_chunk_processing_settings(chunk_stats, config)
    
    # Configuration used
    report['configuration'] = {
        'chunk_size': config.CHUNK_SIZE,
        'chunk_overlap': config.CHUNK_OVERLAP,
        'min_chunk_length': config.MIN_CHUNK_LENGTH,
        'processing_batch_size': config.PROCESSING_BATCH_SIZE
    }
    
    return report


def save_chunk_processing_report(report, log_dir="./logs"):
    """
    Save chunk processing report to file
    
    Args:
        report: Chunk processing report
        log_dir: Directory for log files
    
    Returns:
        str: Path to saved report file
    """
    try:
        import os
        import json
        from datetime import datetime
        from .utils import ensure_directory_exists
        
        # Ensure log directory exists
        if not ensure_directory_exists(log_dir):
            return None
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(log_dir, f"chunk_processing_report_{timestamp}.json")
        
        # Convert report to JSON-serializable format
        json_report = {
            'timestamp': datetime.fromtimestamp(report['timestamp']).isoformat(),
            'summary': report['summary'],
            'quality_analysis': report['quality_analysis'],
            'distribution_stats': report['distribution_stats'],
            'validation_results': report['validation_results'],
            'optimization_suggestions': report['optimization_suggestions'],
            'configuration': report['configuration']
        }
        
        # Save to file
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Chunk processing report saved to: {report_file}")
        return report_file
        
    except Exception as e:
        print(f"⚠️ Could not save chunk processing report: {e}")
        return None
