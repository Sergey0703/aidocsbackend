#!/usr/bin/env python3
"""Test HybridChunker with all JSON files"""

from pathlib import Path
from docling_core.types import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from transformers import AutoTokenizer

# Initialize HybridChunker once
print(f"Initializing HybridChunker...")
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
chunker = HybridChunker(
    tokenizer=tokenizer,
    max_tokens=512,
    merge_peers=True
)

# Test all JSON files
json_dir = Path("rag_indexer/data/json")
json_files = list(json_dir.glob("*.json"))

print(f"\nTesting {len(json_files)} JSON files:\n")

for json_path in json_files:
    print(f"{'='*70}")
    print(f"File: {json_path.name}")
    print(f"{'='*70}")

    try:
        # Load JSON
        doc = DoclingDocument.load_from_json(str(json_path))

        print(f"Structure:")
        print(f"  Texts: {len(doc.texts)}")
        print(f"  Pictures: {len(doc.pictures)}")
        print(f"  Tables: {len(doc.tables)}")
        print(f"  Groups: {len(doc.groups)}")
        print(f"  Body children: {len(doc.body.children)}")

        # Chunk
        chunk_iter = chunker.chunk(dl_doc=doc)
        chunks = list(chunk_iter)

        print(f"\nResult: {len(chunks)} chunks")

        if len(chunks) > 0:
            print(f"First chunk preview: {chunks[0].text[:100]}...")
        else:
            print("WARNING: No chunks created!")
            # Debug: check body structure
            print(f"\nBody label: {doc.body.label}")
            print(f"Body children types:")
            for child in doc.body.children[:3]:  # First 3 children
                print(f"  - {child}")

    except Exception as e:
        print(f"ERROR: {e}")

    print()
