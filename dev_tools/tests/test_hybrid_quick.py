#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test for Hybrid Chunking"""

import sys
from pathlib import Path

# Add rag_indexer to path
sys.path.insert(0, str(Path(__file__).parent / "rag_indexer"))

from chunking_vectors.config import Config
from chunking_vectors.hybrid_chunker import create_hybrid_chunker, is_hybrid_chunking_available
from llama_index.core import Document

def main():
    print("=" * 60)
    print("HYBRID CHUNKING QUICK TEST")
    print("=" * 60)

    # Check availability
    print(f"\n1. Checking HybridChunker availability...")
    if not is_hybrid_chunking_available():
        print("   ERROR: HybridChunker not available!")
        print("   Install with: pip install 'docling-core[chunking]'")
        return
    print("   OK: HybridChunker is available")

    # Load config
    print(f"\n2. Loading configuration...")
    config = Config()
    hybrid_settings = config.get_hybrid_chunking_settings()
    print(f"   Enabled: {hybrid_settings['enabled']}")
    print(f"   Max tokens: {hybrid_settings['max_tokens']}")
    print(f"   Tokenizer: {hybrid_settings['tokenizer']}")
    print(f"   Tokenizer model: {hybrid_settings['tokenizer_model']}")

    if not hybrid_settings['enabled']:
        print("   WARNING: Hybrid chunking is disabled in config!")
        return

    # Create chunker
    print(f"\n3. Creating HybridChunker...")
    try:
        chunker = create_hybrid_chunker(config)
        print(f"   OK: HybridChunker created successfully")
    except Exception as e:
        print(f"   ERROR: Failed to create chunker: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test with sample document
    print(f"\n4. Testing with sample markdown document...")
    test_doc = Document(
        text="""# Test Document

This is a test paragraph with some content.

## Section 1

Here is some text in section 1.

### Subsection 1.1

More detailed content here.

## Section 2

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |

Some text after the table.

## Section 3

- Item 1
- Item 2
- Item 3

Final paragraph with conclusion.
""",
        metadata={
            'file_name': 'test.md',
            'file_path': '/test/test.md',
            'registry_id': '12345678-1234-1234-1234-123456789012'
        }
    )

    try:
        nodes = chunker.chunk_documents([test_doc])
        print(f"   OK: Created {len(nodes)} chunks")

        # Analyze chunks
        print(f"\n5. Chunk Analysis:")
        for i, node in enumerate(nodes[:5]):  # Show first 5
            chunk_text = node.text if hasattr(node, 'text') else str(node)
            chunk_size = len(chunk_text)
            chunk_type = node.metadata.get('chunk_type', 'unknown') if hasattr(node, 'metadata') else 'unknown'
            doc_items = node.metadata.get('doc_items', []) if hasattr(node, 'metadata') else []

            print(f"\n   Chunk {i+1}:")
            print(f"     Size: {chunk_size} chars")
            print(f"     Type: {chunk_type}")
            print(f"     Doc items: {doc_items}")
            print(f"     Preview: {chunk_text[:100]}...")

            # Check metadata preservation
            if hasattr(node, 'metadata'):
                if 'file_name' in node.metadata:
                    print(f"     Metadata preserved: file_name={node.metadata['file_name']}")
                if 'registry_id' in node.metadata:
                    print(f"     Metadata preserved: registry_id={node.metadata['registry_id']}")

        print(f"\n" + "=" * 60)
        print("TEST SUCCESSFUL!")
        print(f"Hybrid chunking is working correctly")
        print("=" * 60)

    except Exception as e:
        print(f"   ERROR: Chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main()
