#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test and Compare Hybrid Chunking vs SentenceSplitter
Comprehensive testing script for migration validation
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chunking_vectors.config import Config
from chunking_vectors.markdown_loader import MarkdownLoader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import Document


def load_test_documents(config: Config, limit: int = None) -> List[Document]:
    """Load test documents from markdown directory"""
    print("📁 Loading test documents...")

    loader = MarkdownLoader(
        input_dir=config.DOCUMENTS_DIR,
        recursive=False,
        config=config
    )

    docs, stats = loader.load_data()

    if limit:
        docs = docs[:limit]

    print(f"   ✅ Loaded {len(docs)} documents")
    return docs


def test_sentence_splitter(docs: List[Document], config: Config) -> Dict[str, Any]:
    """Test SentenceSplitter chunking"""
    print("\n🧪 Testing SentenceSplitter...")

    chunk_settings = config.get_chunk_settings()
    splitter = SentenceSplitter(
        chunk_size=chunk_settings['chunk_size'],
        chunk_overlap=chunk_settings['chunk_overlap'],
        paragraph_separator="\n\n",
        include_metadata=True
    )

    start_time = time.time()
    chunks = []

    for doc in docs:
        try:
            nodes = splitter.get_nodes_from_documents([doc])
            chunks.extend(nodes)
        except Exception as e:
            print(f"   ⚠️  Error chunking {doc.metadata.get('file_name', 'unknown')}: {e}")
            continue

    processing_time = time.time() - start_time

    # Analyze chunks
    chunk_sizes = [len(c.text) for c in chunks]
    metadata_keys = set()
    for c in chunks:
        metadata_keys.update(c.metadata.keys())

    results = {
        'method': 'SentenceSplitter',
        'total_chunks': len(chunks),
        'processing_time': processing_time,
        'chunks_per_doc': len(chunks) / len(docs) if docs else 0,
        'chunk_size_min': min(chunk_sizes) if chunk_sizes else 0,
        'chunk_size_max': max(chunk_sizes) if chunk_sizes else 0,
        'chunk_size_avg': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
        'metadata_keys': sorted(metadata_keys),
        'sample_chunks': [
            {
                'text': c.text[:200] + '...' if len(c.text) > 200 else c.text,
                'size': len(c.text),
                'metadata_keys': list(c.metadata.keys())
            }
            for c in chunks[:3]
        ]
    }

    print(f"   ✅ Created {len(chunks)} chunks in {processing_time:.2f}s")
    print(f"   Avg: {results['chunk_size_avg']:.0f} chars/chunk")

    return results


def test_hybrid_chunker(docs: List[Document], config: Config) -> Dict[str, Any]:
    """Test HybridChunker"""
    print("\n🧪 Testing HybridChunker...")

    try:
        from chunking_vectors.hybrid_chunker import create_hybrid_chunker, is_hybrid_chunking_available

        if not is_hybrid_chunking_available():
            print("   ❌ Hybrid chunking not available!")
            print("   Install with: pip install 'docling-core[chunking]' transformers")
            return None

        # Enable hybrid chunking
        config.USE_HYBRID_CHUNKING = True

        chunker = create_hybrid_chunker(config)

        start_time = time.time()
        chunks = chunker.chunk_documents(docs)
        processing_time = time.time() - start_time

        # Analyze chunks
        chunk_sizes = [len(c.text) for c in chunks]
        metadata_keys = set()
        for c in chunks:
            metadata_keys.update(c.metadata.keys())

        # Count chunk types
        chunk_types = {}
        for c in chunks:
            chunk_type = c.metadata.get('chunk_type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

        results = {
            'method': 'HybridChunker',
            'total_chunks': len(chunks),
            'processing_time': processing_time,
            'chunks_per_doc': len(chunks) / len(docs) if docs else 0,
            'chunk_size_min': min(chunk_sizes) if chunk_sizes else 0,
            'chunk_size_max': max(chunk_sizes) if chunk_sizes else 0,
            'chunk_size_avg': sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
            'metadata_keys': sorted(metadata_keys),
            'chunk_types': chunk_types,
            'sample_chunks': [
                {
                    'text': c.text[:200] + '...' if len(c.text) > 200 else c.text,
                    'size': len(c.text),
                    'metadata_keys': list(c.metadata.keys()),
                    'chunk_type': c.metadata.get('chunk_type', 'unknown'),
                    'doc_items': c.metadata.get('doc_items', [])
                }
                for c in chunks[:3]
            ]
        }

        print(f"   ✅ Created {len(chunks)} chunks in {processing_time:.2f}s")
        print(f"   Avg: {results['chunk_size_avg']:.0f} chars/chunk")
        if chunk_types:
            print(f"   Chunk types: {chunk_types}")

        return results

    except Exception as e:
        print(f"   ❌ Hybrid chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_results(sentence_results: Dict, hybrid_results: Dict):
    """Compare chunking results"""
    print("\n" + "=" * 80)
    print("📊 CHUNKING COMPARISON RESULTS")
    print("=" * 80)

    if not hybrid_results:
        print("⚠️  Hybrid chunking not available - comparison skipped")
        return

    # Chunk count comparison
    print(f"\n🔢 Chunk Count:")
    print(f"   SentenceSplitter: {sentence_results['total_chunks']}")
    print(f"   HybridChunker:    {hybrid_results['total_chunks']}")
    diff = hybrid_results['total_chunks'] - sentence_results['total_chunks']
    diff_pct = (diff / sentence_results['total_chunks'] * 100) if sentence_results['total_chunks'] > 0 else 0
    print(f"   Difference:       {diff:+d} ({diff_pct:+.1f}%)")

    # Processing time comparison
    print(f"\n⏱️  Processing Time:")
    print(f"   SentenceSplitter: {sentence_results['processing_time']:.2f}s")
    print(f"   HybridChunker:    {hybrid_results['processing_time']:.2f}s")
    time_diff = hybrid_results['processing_time'] - sentence_results['processing_time']
    time_diff_pct = (time_diff / sentence_results['processing_time'] * 100) if sentence_results['processing_time'] > 0 else 0
    print(f"   Difference:       {time_diff:+.2f}s ({time_diff_pct:+.1f}%)")

    # Chunk size comparison
    print(f"\n📏 Chunk Size (chars):")
    print(f"   Method           | Min    | Max    | Avg")
    print(f"   {'─'*17}+{'─'*8}+{'─'*8}+{'─'*8}")
    print(f"   SentenceSplitter | {sentence_results['chunk_size_min']:6.0f} | {sentence_results['chunk_size_max']:6.0f} | {sentence_results['chunk_size_avg']:6.0f}")
    print(f"   HybridChunker    | {hybrid_results['chunk_size_min']:6.0f} | {hybrid_results['chunk_size_max']:6.0f} | {hybrid_results['chunk_size_avg']:6.0f}")

    # Metadata comparison
    print(f"\n📋 Metadata Keys:")
    sentence_keys = set(sentence_results['metadata_keys'])
    hybrid_keys = set(hybrid_results['metadata_keys'])

    common_keys = sentence_keys & hybrid_keys
    sentence_only = sentence_keys - hybrid_keys
    hybrid_only = hybrid_keys - sentence_keys

    print(f"   Common:         {sorted(common_keys)}")
    if sentence_only:
        print(f"   SentenceSplitter only: {sorted(sentence_only)}")
    if hybrid_only:
        print(f"   HybridChunker only:    {sorted(hybrid_only)}")

    # Chunk types (Hybrid only)
    if 'chunk_types' in hybrid_results:
        print(f"\n🏷️  Chunk Types (HybridChunker):")
        for chunk_type, count in sorted(hybrid_results['chunk_types'].items()):
            pct = (count / hybrid_results['total_chunks'] * 100) if hybrid_results['total_chunks'] > 0 else 0
            print(f"   {chunk_type:15s}: {count:5d} ({pct:5.1f}%)")

    print("=" * 80)

    # Quality assessment
    print(f"\n💡 Quality Assessment:")

    if abs(diff_pct) < 10:
        print(f"   ✅ Chunk count difference is small ({diff_pct:.1f}%) - good consistency")
    elif diff_pct < 0:
        print(f"   ⚠️  HybridChunker creates fewer chunks ({diff_pct:.1f}%) - larger chunks, less splitting")
    else:
        print(f"   ℹ️  HybridChunker creates more chunks ({diff_pct:.1f}%) - finer granularity")

    if time_diff_pct < 50:
        print(f"   ✅ Processing time difference is acceptable ({time_diff_pct:.1f}%)")
    else:
        print(f"   ⚠️  HybridChunker is significantly slower ({time_diff_pct:.1f}%) - consider batch size tuning")

    if hybrid_only:
        print(f"   ✅ HybridChunker provides richer metadata: {sorted(hybrid_only)}")

    print()


def save_comparison_report(sentence_results: Dict, hybrid_results: Dict, output_dir: str = "./reports"):
    """Save comparison report to JSON"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    filename = f"chunking_comparison_{timestamp}.json"
    output_path = output_dir / filename

    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'sentence_splitter': sentence_results,
        'hybrid_chunker': hybrid_results,
        'comparison': {
            'chunk_count_diff': (hybrid_results['total_chunks'] - sentence_results['total_chunks']) if hybrid_results else None,
            'chunk_count_diff_pct': ((hybrid_results['total_chunks'] - sentence_results['total_chunks']) / sentence_results['total_chunks'] * 100) if hybrid_results and sentence_results['total_chunks'] > 0 else None,
            'processing_time_diff': (hybrid_results['processing_time'] - sentence_results['processing_time']) if hybrid_results else None,
            'metadata_keys_added': sorted(set(hybrid_results['metadata_keys']) - set(sentence_results['metadata_keys'])) if hybrid_results else [],
        }
    }

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 Comparison report saved: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"❌ Failed to save report: {e}")
        return None


def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 HYBRID CHUNKING TEST & COMPARISON")
    print("=" * 80)

    # Load config
    try:
        config = Config()
        print(f"✅ Configuration loaded")
        print(f"   Documents dir: {config.DOCUMENTS_DIR}")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return 1

    # Load test documents
    try:
        docs = load_test_documents(config, limit=20)  # Limit to 20 for testing
        if not docs:
            print("❌ No documents found!")
            return 1
    except Exception as e:
        print(f"❌ Failed to load documents: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test SentenceSplitter
    try:
        sentence_results = test_sentence_splitter(docs, config)
    except Exception as e:
        print(f"❌ SentenceSplitter test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test HybridChunker
    try:
        hybrid_results = test_hybrid_chunker(docs, config)
    except Exception as e:
        print(f"❌ HybridChunker test failed: {e}")
        import traceback
        traceback.print_exc()
        hybrid_results = None

    # Compare results
    if hybrid_results:
        compare_results(sentence_results, hybrid_results)

        # Save report
        save_comparison_report(sentence_results, hybrid_results)

        print("\n✅ Test completed successfully!")
        return 0
    else:
        print("\n⚠️  Test completed with warnings (Hybrid chunking not available)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
