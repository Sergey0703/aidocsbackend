#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test the failed file to find the issue"""

import sys
from pathlib import Path

# Add rag_indexer to path
sys.path.insert(0, str(Path(__file__).parent / "rag_indexer"))

from chunking_vectors.markdown_loader import MarkdownLoader
from chunking_vectors.config import Config
from chunking_vectors.registry_manager import DocumentRegistryManager

def main():
    print("=" * 60)
    print("TESTING FAILED FILE: Vehicle Registration Certificate.md")
    print("=" * 60)

    # Setup
    config = Config()

    # Test 1: Check file exists and readable
    print("\n1. Checking file...")
    md_file = Path("rag_indexer/data/markdown/Vehicle Registration Certificate.md")
    json_file = Path("rag_indexer/data/json/Vehicle Registration Certificate.json")

    print(f"   Markdown exists: {md_file.exists()}")
    print(f"   JSON exists: {json_file.exists()}")

    if not md_file.exists():
        print("   ERROR: Markdown file not found!")
        return

    # Test 2: Read file content
    print("\n2. Reading file content...")
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"   Content length: {len(content)} chars")
        print(f"   Preview: {content[:200]}...")
    except Exception as e:
        print(f"   ERROR reading file: {e}")
        return

    # Test 3: Try to load with MarkdownLoader
    print("\n3. Testing MarkdownLoader...")
    try:
        loader = MarkdownLoader(
            input_dir=str(md_file.parent),
            recursive=False,
            config=config
        )

        # Connect to registry
        registry = DocumentRegistryManager(config.CONNECTION_STRING)

        # Load documents
        docs, stats = loader.load_data(registry_manager=registry)

        print(f"   Documents loaded: {len(docs)}")
        print(f"   Stats: {stats}")

        # Find our document
        our_doc = None
        for doc in docs:
            if 'Vehicle Registration Certificate' in doc.metadata.get('file_name', ''):
                our_doc = doc
                break

        if our_doc:
            print(f"\n4. Found document:")
            print(f"   File name: {our_doc.metadata.get('file_name')}")
            print(f"   Registry ID: {our_doc.metadata.get('registry_id')}")
            print(f"   JSON path: {our_doc.metadata.get('json_path')}")
            print(f"   Content length: {len(our_doc.text)}")

            # Test 4: Try hybrid chunking
            print(f"\n5. Testing Hybrid Chunking...")
            from chunking_vectors.hybrid_chunker import create_hybrid_chunker

            chunker = create_hybrid_chunker(config)
            chunks = chunker.chunk_documents([our_doc])

            print(f"   Chunks created: {len(chunks)}")

            if len(chunks) == 0:
                print("   ERROR: No chunks created!")
                print("\n6. Checking JSON loading...")

                # Try to load JSON directly
                json_path = our_doc.metadata.get('json_path')
                if json_path and Path(json_path).exists():
                    from docling_core.types.doc import DoclingDocument
                    try:
                        dl_doc = DoclingDocument.load_from_json(json_path)
                        print(f"   JSON loaded successfully")
                        print(f"   Document name: {dl_doc.name}")
                        print(f"   Main text length: {len(dl_doc.main_text) if hasattr(dl_doc, 'main_text') else 'N/A'}")
                    except Exception as e:
                        print(f"   ERROR loading JSON: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"   ERROR: JSON path not found or invalid: {json_path}")
            else:
                print(f"   SUCCESS: Chunks created!")
                for i, chunk in enumerate(chunks[:3]):
                    print(f"      Chunk {i+1}: {len(chunk.text)} chars")
        else:
            print(f"\n   ERROR: Document not found in loaded documents!")
            print(f"   Available files: {[d.metadata.get('file_name') for d in docs]}")

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
