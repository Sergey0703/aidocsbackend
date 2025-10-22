#!/usr/bin/env python3
"""Test HybridChunker with Vehicle Registration Certificate JSON"""

from pathlib import Path
from docling_core.types import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from transformers import AutoTokenizer

# Load JSON
json_path = Path("rag_indexer/data/json/Vehicle Registration Certificate.json")
print(f"Loading JSON: {json_path}")
doc = DoclingDocument.load_from_json(str(json_path))

print(f"\nDoclingDocument loaded:")
print(f"  Name: {doc.name}")
print(f"  Texts: {len(doc.texts)}")
print(f"  Pictures: {len(doc.pictures)}")
print(f"  Tables: {len(doc.tables)}")
print(f"  Groups: {len(doc.groups)}")
print(f"  Body children: {len(doc.body.children)}")

# Initialize HybridChunker
print(f"\nInitializing HybridChunker...")
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
chunker = HybridChunker(
    tokenizer=tokenizer,
    max_tokens=512,
    merge_peers=True
)

print(f"HybridChunker initialized")

# Chunk the document
print(f"\nChunking document...")
try:
    chunk_iter = chunker.chunk(dl_doc=doc)
    chunks = list(chunk_iter)
    print(f"Created {len(chunks)} chunks")

    if len(chunks) == 0:
        print("\nWARNING: No chunks created!")
        print("\nDocument structure:")
        print(f"  Body: {doc.body}")
        print(f"  Body children: {doc.body.children}")

        # Try to understand what's in the document
        if doc.body.children:
            print(f"\n  First child: {doc.body.children[0]}")
    else:
        print("\nFirst chunk:")
        print(f"  Text: {chunks[0].text[:200]}...")
        print(f"  Metadata: {chunks[0].meta}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
