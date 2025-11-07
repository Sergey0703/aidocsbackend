#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Hybrid Chunking with real Docling JSON"""

import sys
from pathlib import Path

# Add rag_indexer to path
sys.path.insert(0, str(Path(__file__).parent / "rag_indexer"))

from chunking_vectors.config import Config
from chunking_vectors.hybrid_chunker import create_hybrid_chunker, is_hybrid_chunking_available
from llama_index.core import Document

def main():
    print("=" * 60)
    print("HYBRID CHUNKING WITH REAL JSON TEST")
    print("=" * 60)

    # Check availability
    print(f"\n1. Checking HybridChunker availability...")
    if not is_hybrid_chunking_available():
        print("   ERROR: HybridChunker not available!")
        return False
    print("   [+] HybridChunker is available")

    # Load config
    print(f"\n2. Loading configuration...")
    config = Config()
    hybrid_settings = config.get_hybrid_chunking_settings()
    print(f"   Enabled: {hybrid_settings['enabled']}")
    print(f"   Max tokens: {hybrid_settings['max_tokens']}")

    if not hybrid_settings['enabled']:
        print("   ERROR: Hybrid chunking is disabled in config!")
        return False

    # Find JSON file (in data/json at project root)
    json_dir = Path(__file__).parent / "data" / "json"
    json_files = list(json_dir.glob("*.json"))

    if not json_files:
        print(f"\n   ERROR: No JSON files found in {json_dir}")
        return False

    json_file = json_files[0]
    print(f"\n3. Using JSON: {json_file.name}")
    print(f"   Size: {json_file.stat().st_size:,} bytes")

    # Find corresponding markdown (in data/markdown at project root)
    md_dir = Path(__file__).parent / "data" / "markdown"
    md_file = md_dir / f"{json_file.stem}.md"

    if not md_file.exists():
        print(f"   ERROR: Markdown file not found: {md_file}")
        return False

    # Read markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    print(f"   Markdown size: {len(markdown_content):,} chars")

    # Create test document with json_path
    test_doc = Document(
        text=markdown_content,
        metadata={
            'file_name': md_file.name,
            'file_path': str(md_file),
            'json_path': str(json_file),  # KEY: Point to JSON
            'registry_id': '12345678-1234-1234-1234-123456789012'
        }
    )

    # Create chunker
    print(f"\n4. Creating HybridChunker...")
    try:
        chunker = create_hybrid_chunker(config)
        print(f"   [+] HybridChunker created")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Chunk document
    print(f"\n5. Chunking document with JSON...")
    try:
        nodes = chunker.chunk_documents([test_doc])
        print(f"   [+] Created {len(nodes)} chunks")

        if len(nodes) == 0:
            print("   ERROR: No chunks created!")
            return False

        # Analyze chunks
        print(f"\n6. Chunk Analysis:")
        for i, node in enumerate(nodes[:5]):  # Show first 5
            chunk_text = node.text if hasattr(node, 'text') else str(node)
            chunk_size = len(chunk_text)
            chunk_type = node.metadata.get('chunk_type', 'unknown') if hasattr(node, 'metadata') else 'unknown'
            doc_items = node.metadata.get('doc_items', []) if hasattr(node, 'metadata') else []
            chunking_method = node.metadata.get('chunking_method', 'unknown') if hasattr(node, 'metadata') else 'unknown'

            print(f"\n   Chunk {i+1}:")
            print(f"     Size: {chunk_size} chars")
            print(f"     Type: {chunk_type}")
            print(f"     Method: {chunking_method}")
            print(f"     Doc items: {doc_items}")
            print(f"     Preview: {chunk_text[:150]}...")

            # Check metadata preservation
            if hasattr(node, 'metadata'):
                if 'file_name' in node.metadata:
                    print(f"     [+] Metadata preserved: file_name={node.metadata['file_name']}")
                if 'registry_id' in node.metadata:
                    print(f"     [+] Metadata preserved: registry_id={node.metadata['registry_id']}")

        print(f"\n" + "=" * 60)
        print("TEST SUCCESSFUL!")
        print(f"Hybrid chunking with JSON is working correctly!")
        print(f"Created {len(nodes)} structure-aware chunks")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"   ERROR: Chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
