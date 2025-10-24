#!/usr/bin/env python3
"""Analyze how HybridChunker processes the CVRT document"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add rag_indexer to path
sys.path.insert(0, str(Path(__file__).parent / 'rag_indexer'))

load_dotenv('rag_indexer/.env')

from docling_core.types import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

json_dir = os.getenv('JSON_OUTPUT_DIR', 'rag_indexer/data/json')
cvrt_json = Path(json_dir) / '1761320270_CVRT_Pass_Statement.json'

print("\n" + "="*80)
print("ANALYZING HYBRID CHUNKING BEHAVIOR")
print("="*80 + "\n")

if not cvrt_json.exists():
    print(f"ERROR: JSON file not found: {cvrt_json}")
    exit(1)

# Load DoclingDocument
print(f"Loading DoclingDocument from: {cvrt_json}")
docling_doc = DoclingDocument.load_from_json(cvrt_json)

print(f"Document name: {docling_doc.name}")
print(f"Document structure:")
print(f"  Texts: {len(list(docling_doc.texts))}")
print(f"  Tables: {len(list(docling_doc.tables))}")
print(f"  Pages: {len(list(docling_doc.pages))}")
print()

# Initialize tokenizer (matching config.py settings)
print("Initializing HuggingFace tokenizer...")
hf_tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
tokenizer = HuggingFaceTokenizer(
    tokenizer=hf_tokenizer,
    max_tokens=512  # From config
)

# Initialize HybridChunker with different merge_peers settings
print("\n" + "="*80)
print("TEST 1: HybridChunker with merge_peers=True (current setting)")
print("="*80)

chunker_merged = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=True  # Current setting
)

chunks_merged = list(chunker_merged.chunk(dl_doc=docling_doc))
print(f"\nTotal chunks created: {len(chunks_merged)}")

# Analyze chunk content
chunk_texts = [c.text for c in chunks_merged]
unique_chunks = set(chunk_texts)
print(f"Unique chunks: {len(unique_chunks)}")
print(f"Duplicate chunks: {len(chunk_texts) - len(unique_chunks)}")

# Find most duplicated chunks
from collections import Counter
chunk_counts = Counter(chunk_texts)
most_common = chunk_counts.most_common(10)
print(f"\nTop 10 most duplicated chunks:")
for i, (text, count) in enumerate(most_common, 1):
    if count > 1:
        print(f"  {i}. Appears {count} times: {text[:80]}...")

# Analyze chunk types
print(f"\n\nChunk length statistics:")
chunk_lengths = [len(c.text) for c in chunks_merged]
print(f"  Min: {min(chunk_lengths)} chars")
print(f"  Max: {max(chunk_lengths)} chars")
print(f"  Avg: {sum(chunk_lengths) / len(chunk_lengths):.0f} chars")

# Sample some chunks
print(f"\n\nFirst 10 chunks:")
for i, chunk in enumerate(chunks_merged[:10], 1):
    print(f"\n[Chunk {i}] Length: {len(chunk.text)}")
    print(f"Text: {chunk.text[:150]}...")
    if hasattr(chunk, 'meta') and chunk.meta:
        if hasattr(chunk.meta, 'doc_items') and chunk.meta.doc_items:
            labels = [item.label.value if hasattr(item.label, 'value') else str(item.label)
                     for item in chunk.meta.doc_items]
            print(f"Doc items: {labels}")

# TEST 2: Try merge_peers=False
print("\n\n" + "="*80)
print("TEST 2: HybridChunker with merge_peers=False")
print("="*80)

chunker_unmerged = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=False
)

chunks_unmerged = list(chunker_unmerged.chunk(dl_doc=docling_doc))
print(f"\nTotal chunks created: {len(chunks_unmerged)}")

chunk_texts_unmerged = [c.text for c in chunks_unmerged]
unique_chunks_unmerged = set(chunk_texts_unmerged)
print(f"Unique chunks: {len(unique_chunks_unmerged)}")
print(f"Duplicate chunks: {len(chunk_texts_unmerged) - len(unique_chunks_unmerged)}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print(f"Current setting (merge_peers=True): {len(chunks_merged)} chunks, {len(chunk_texts) - len(unique_chunks)} duplicates")
print(f"Alternative (merge_peers=False): {len(chunks_unmerged)} chunks, {len(chunk_texts_unmerged) - len(unique_chunks_unmerged)} duplicates")
print()
