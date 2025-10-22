#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Updated chunk_helpers.py with Hybrid Chunking support
UPDATED: Adds hybrid chunking path while maintaining backward compatibility

This file shows ONLY the changes needed in chunk_helpers.py
Copy these functions to replace the corresponding ones in chunk_helpers.py
"""

import logging
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def create_and_filter_chunks_enhanced(documents, node_parser, config, stats):
    """
    Create and filter chunks from documents
    UPDATED: Now supports both SentenceSplitter and HybridChunker

    Args:
        documents: List of LlamaIndex Document objects
        node_parser: SentenceSplitter instance (or None if using HybridChunker)
        config: Configuration object
        stats: Statistics dictionary to update

    Returns:
        tuple: (all_nodes, valid_nodes, filtered_count, processing_report)
    """
    start_time = time.time()

    # Initialize report
    processing_report = {
        'total_documents': len(documents),
        'chunking_method': None,
        'total_chunks': 0,
        'valid_chunks': 0,
        'filtered_chunks': 0,
        'filter_reasons': {},
        'processing_time': 0,
        'chunks_per_document': [],
        'chunk_size_stats': {'min': 0, 'max': 0, 'avg': 0},
    }

    # Choose chunking method based on config
    hybrid_settings = config.get_hybrid_chunking_settings() if hasattr(config, 'get_hybrid_chunking_settings') else {'enabled': False}
    use_hybrid = hybrid_settings.get('enabled', False)

    if use_hybrid:
        logger.info("[*] Using Hybrid Chunking (Docling HybridChunker)")
        processing_report['chunking_method'] = 'hybrid_docling'

        try:
            from chunking_vectors.hybrid_chunker import create_hybrid_chunker, is_hybrid_chunking_available

            if not is_hybrid_chunking_available():
                logger.error("[-] Hybrid chunking requested but not available! Falling back to SentenceSplitter.")
                logger.error("   Install with: pip install 'docling-core[chunking]' transformers")
                use_hybrid = False
                processing_report['chunking_method'] = 'sentence_splitter_fallback'
            else:
                # Create hybrid chunker
                chunker = create_hybrid_chunker(config)
                all_nodes = chunker.chunk_documents(documents)

                logger.info(f"   [+] Hybrid chunking created {len(all_nodes)} chunks from {len(documents)} documents")

        except Exception as e:
            logger.error(f"[-] Hybrid chunking failed: {e}")
            logger.error("   Falling back to SentenceSplitter")
            use_hybrid = False
            processing_report['chunking_method'] = 'sentence_splitter_fallback'
            import traceback
            logger.error(traceback.format_exc())

    if not use_hybrid:
        # Legacy path: SentenceSplitter
        logger.info("[*] Using Legacy Chunking (SentenceSplitter)")
        processing_report['chunking_method'] = 'sentence_splitter'

        if node_parser is None:
            raise ValueError("node_parser is required for SentenceSplitter chunking")

        all_nodes = []
        for doc in documents:
            try:
                nodes = node_parser.get_nodes_from_documents([doc])
                all_nodes.extend(nodes)
            except Exception as e:
                logger.error(f"Failed to chunk document {doc.metadata.get('file_name', 'unknown')}: {e}")
                continue

        logger.info(f"   [+] SentenceSplitter created {len(all_nodes)} chunks from {len(documents)} documents")

    # Update report
    processing_report['total_chunks'] = len(all_nodes)

    # Filter chunks (same logic for both methods)
    valid_nodes = []
    filtered_count = 0
    filter_reasons = {}

    min_chunk_length = config.MIN_CHUNK_LENGTH if hasattr(config, 'MIN_CHUNK_LENGTH') else 50

    for node in all_nodes:
        try:
            # Get content
            content = node.text if hasattr(node, 'text') else node.get_content()

            # Filter criteria
            if len(content.strip()) < min_chunk_length:
                filtered_count += 1
                filter_reasons['too_short'] = filter_reasons.get('too_short', 0) + 1
                continue

            # Check for null bytes (data quality)
            if '\x00' in content or '\u0000' in content:
                filtered_count += 1
                filter_reasons['null_bytes'] = filter_reasons.get('null_bytes', 0) + 1
                logger.warning(f"Filtered chunk with null bytes from {node.metadata.get('file_name', 'unknown')}")
                continue

            # Valid chunk
            valid_nodes.append(node)

        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            filtered_count += 1
            filter_reasons['processing_error'] = filter_reasons.get('processing_error', 0) + 1
            continue

    # Calculate chunk size statistics
    if valid_nodes:
        chunk_sizes = [len(node.text if hasattr(node, 'text') else node.get_content()) for node in valid_nodes]
        processing_report['chunk_size_stats'] = {
            'min': min(chunk_sizes),
            'max': max(chunk_sizes),
            'avg': sum(chunk_sizes) / len(chunk_sizes)
        }

    # Calculate chunks per document
    from collections import Counter
    doc_chunks = Counter()
    for node in valid_nodes:
        filename = node.metadata.get('file_name', 'unknown')
        doc_chunks[filename] += 1

    processing_report['chunks_per_document'] = [
        {'filename': filename, 'chunks': count}
        for filename, count in doc_chunks.most_common(10)  # Top 10
    ]

    # Finalize report
    processing_report['valid_chunks'] = len(valid_nodes)
    processing_report['filtered_chunks'] = filtered_count
    processing_report['filter_reasons'] = filter_reasons
    processing_report['processing_time'] = time.time() - start_time

    # Update stats
    stats['chunks_created'] = len(all_nodes)
    stats['valid_chunks'] = len(valid_nodes)
    stats['filtered_chunks'] = filtered_count

    # Print summary
    logger.info(f"[+] Chunking complete:")
    logger.info(f"   Method: {processing_report['chunking_method']}")
    logger.info(f"   Total chunks: {len(all_nodes)}")
    logger.info(f"   Valid chunks: {len(valid_nodes)}")
    logger.info(f"   Filtered: {filtered_count}")
    if filter_reasons:
        logger.info(f"   Filter reasons: {filter_reasons}")
    logger.info(f"   Avg chunk size: {processing_report['chunk_size_stats']['avg']:.0f} chars")
    logger.info(f"   Processing time: {processing_report['processing_time']:.2f}s")

    return all_nodes, valid_nodes, filtered_count, processing_report


def create_chunk_processing_report(processing_report, config):
    """
    Create detailed chunk processing report
    UPDATED: Includes hybrid chunking information

    Args:
        processing_report: Report from create_and_filter_chunks_enhanced
        config: Configuration object

    Returns:
        dict: Detailed report
    """
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'chunking_configuration': {},
        'processing_results': processing_report,
        'quality_metrics': {}
    }

    # Add chunking configuration
    chunking_method = processing_report.get('chunking_method', 'sentence_splitter')

    if chunking_method in ['hybrid_docling', 'sentence_splitter_fallback']:
        # Hybrid chunking config
        hybrid_settings = config.get_hybrid_chunking_settings() if hasattr(config, 'get_hybrid_chunking_settings') else {}
        report['chunking_configuration'] = {
            'method': 'hybrid_docling',
            'max_tokens': hybrid_settings.get('max_tokens', 512),
            'merge_peers': hybrid_settings.get('merge_peers', True),
            'use_contextualize': hybrid_settings.get('use_contextualize', False),
            'tokenizer': hybrid_settings.get('tokenizer', 'huggingface'),
            'tokenizer_model': hybrid_settings.get('tokenizer_model', 'unknown'),
        }
    else:
        # SentenceSplitter config
        chunk_settings = config.get_chunk_settings() if hasattr(config, 'get_chunk_settings') else {}
        report['chunking_configuration'] = {
            'method': 'sentence_splitter',
            'chunk_size': chunk_settings.get('chunk_size', 512),
            'chunk_overlap': chunk_settings.get('chunk_overlap', 128),
            'min_chunk_length': chunk_settings.get('min_chunk_length', 50),
        }

    # Quality metrics
    total = processing_report['total_chunks']
    valid = processing_report['valid_chunks']

    report['quality_metrics'] = {
        'chunk_retention_rate': (valid / total * 100) if total > 0 else 0,
        'avg_chunks_per_document': valid / processing_report['total_documents'] if processing_report['total_documents'] > 0 else 0,
        'filtering_efficiency': (processing_report['filtered_chunks'] / total * 100) if total > 0 else 0,
    }

    return report


def save_chunk_processing_report(report, output_dir):
    """
    Save chunk processing report to JSON file
    UPDATED: Includes hybrid chunking details

    Args:
        report: Report dictionary
        output_dir: Directory to save report

    Returns:
        str: Path to saved report
    """
    import json
    from pathlib import Path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with chunking method
    method = report['chunking_configuration'].get('method', 'unknown')
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f"chunk_report_{method}_{timestamp}.json"

    output_path = output_dir / filename

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"[*] Chunk processing report saved: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"Failed to save chunk processing report: {e}")
        return None


# Backward compatibility functions
def print_chunk_processing_summary(processing_report):
    """Print chunk processing summary to console"""
    print("\n" + "=" * 60)
    print("[*] CHUNK PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Chunking method: {processing_report['chunking_method']}")
    print(f"Total documents: {processing_report['total_documents']}")
    print(f"Total chunks created: {processing_report['total_chunks']}")
    print(f"Valid chunks: {processing_report['valid_chunks']}")
    print(f"Filtered chunks: {processing_report['filtered_chunks']}")

    if processing_report['filter_reasons']:
        print(f"\nFilter reasons:")
        for reason, count in processing_report['filter_reasons'].items():
            print(f"  {reason}: {count}")

    stats = processing_report['chunk_size_stats']
    print(f"\nChunk size statistics:")
    print(f"  Min: {stats['min']} chars")
    print(f"  Max: {stats['max']} chars")
    print(f"  Avg: {stats['avg']:.0f} chars")

    print(f"\nProcessing time: {processing_report['processing_time']:.2f}s")

    if processing_report['chunks_per_document']:
        print(f"\nTop documents by chunk count:")
        for item in processing_report['chunks_per_document'][:5]:
            print(f"  {item['filename']}: {item['chunks']} chunks")

    print("=" * 60)


if __name__ == "__main__":
    print("[+] chunk_helpers_hybrid.py - Hybrid Chunking Support Module")
    print("This module provides updated functions for chunk_helpers.py")
    print("\nTo integrate:")
    print("1. Copy functions to existing chunk_helpers.py")
    print("2. Or replace chunk_helpers.py entirely")
    print("3. Ensure hybrid_chunker.py is in the same directory")
