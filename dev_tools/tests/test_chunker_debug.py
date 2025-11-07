#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug HybridChunker for Vehicle Registration Certificate"""

import sys
from pathlib import Path

# Add rag_indexer to path
sys.path.insert(0, str(Path(__file__).parent / "rag_indexer"))

from docling_core.types.doc import DoclingDocument
from chunking_vectors.config import Config
from chunking_vectors.hybrid_chunker import create_hybrid_chunker

def main():
    print("=" * 60)
    print("DEBUG: HybridChunker for Vehicle Registration Certificate")
    print("=" * 60)

    # Load JSON
    json_path = "rag_indexer/data/json/Vehicle Registration Certificate.json"
    print(f"\n1. Loading JSON: {json_path}")

    try:
        doc = DoclingDocument.load_from_json(json_path)
        print(f"   Name: {doc.name}")
        print(f"   Pages: {len(doc.pages) if hasattr(doc, 'pages') else 'N/A'}")

        # Inspect document structure
        print(f"\n2. Document structure:")
        if hasattr(doc, 'body'):
            print(f"   Has body: Yes")
            print(f"   Body type: {type(doc.body)}")
            print(f"   Body: {doc.body}")

        if hasattr(doc, 'pages'):
            print(f"\n3. Page details:")
            for i, page in enumerate(doc.pages):
                print(f"   Page {i+1}:")
                print(f"     Size: {page.size if hasattr(page, 'size') else 'N/A'}")
                if hasattr(page, 'cells'):
                    print(f"     Cells: {len(page.cells)}")
                if hasattr(page, 'predictions'):
                    print(f"     Predictions: {page.predictions}")

        # Create chunker
        print(f"\n4. Creating HybridChunker...")
        config = Config()
        chunker = create_hybrid_chunker(config)
        print(f"   Chunker created")

        # Try chunking
        print(f"\n5. Chunking document...")
        try:
            chunk_iter = chunker.chunker.chunk(dl_doc=doc)
            chunks = list(chunk_iter)
            print(f"   Chunks created: {len(chunks)}")

            if len(chunks) == 0:
                print(f"\n   ERROR: No chunks created!")
                print(f"\n6. Debugging why no chunks...")

                # Check if document has any text
                try:
                    text = doc.export_to_markdown()
                    print(f"   Markdown export: {len(text)} chars")
                    print(f"   Preview: {text[:200]}...")
                except Exception as e:
                    print(f"   ERROR exporting markdown: {e}")

                # Check chunker settings
                hybrid_settings = config.get_hybrid_chunking_settings()
                print(f"\n   Chunker settings:")
                print(f"     Max tokens: {hybrid_settings['max_tokens']}")
                print(f"     Merge peers: {hybrid_settings['merge_peers']}")
                print(f"     Tokenizer: {hybrid_settings['tokenizer']}")

            else:
                print(f"\n   SUCCESS!")
                for i, chunk in enumerate(chunks[:3]):
                    print(f"\n   Chunk {i+1}:")
                    print(f"     Text: {chunk.text[:150]}...")
                    print(f"     Metadata: {chunk.meta}")

        except Exception as e:
            print(f"   ERROR chunking: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
