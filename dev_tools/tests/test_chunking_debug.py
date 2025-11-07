#!/usr/bin/env python3
"""
Debug script to test chunking for Vehicle Registration Certificate
"""
import sys
sys.path.insert(0, 'rag_indexer')

import os
from pathlib import Path
from dotenv import load_dotenv
from llama_index.core import Document
import json

# Load env
load_dotenv('rag_indexer/.env')

from storage.storage_manager import SupabaseStorageManager
from chunking_vectors.hybrid_chunker import HybridChunkerWrapper

def test_chunking():
    print("="*80)
    print("Testing HybridChunkerWrapper with Vehicle Registration Certificate")
    print("="*80)

    # Download files from Storage
    storage = SupabaseStorageManager()

    print("\n[1] Downloading markdown from Storage...")
    md_path = storage.download_to_temp('markdown/processed/1761382324_Vehicle_Registration_Certificate.md')

    print("[2] Downloading DoclingDocument JSON from Storage...")
    json_path = storage.download_to_temp('json/processed/1761382324_Vehicle_Registration_Certificate.json')

    # Read markdown content
    print("\n[3] Reading markdown content...")
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    print(f"    Markdown length: {len(md_content)} chars")

    # Read JSON
    print("\n[4] Reading DoclingDocument JSON...")
    with open(json_path, 'r', encoding='utf-8') as f:
        doc_json = json.load(f)
    print(f"    JSON schema: {doc_json.get('schema_name')} v{doc_json.get('version')}")
    print(f"    Texts: {len(doc_json.get('texts', []))}")
    print(f"    Tables: {len(doc_json.get('tables', []))}")
    print(f"    Pages: {len(doc_json.get('pages', []))}")

    # Create LlamaIndex Document
    print("\n[5] Creating LlamaIndex Document...")
    document = Document(
        text=md_content,
        metadata={
            'file_name': '1761382324_Vehicle_Registration_Certificate.md',
            'file_path': str(md_path),
            'json_path': str(json_path),
            'registry_id': 'aa24d13e-1e8d-422d-a1ab-608636de4906',  # Known registry_id
            'original_filename': 'Vehicle Registration Certificate.pdf'
        }
    )
    print(f"    Document created with {len(document.text)} chars")

    # Initialize HybridChunkerWrapper
    print("\n[6] Initializing HybridChunkerWrapper...")
    chunker = HybridChunkerWrapper(max_tokens=512, merge_peers=True)
    print(f"    Chunker initialized: max_tokens={chunker.max_tokens}")

    # Chunk the document
    print("\n[7] Chunking document...")
    chunks = chunker.chunk_single_doc(document)

    print(f"\n[8] RESULT: Created {len(chunks)} chunks")
    print("="*80)

    # Analyze chunks
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  ID: {chunk.id_}")
        print(f"  Text length: {len(chunk.text)} chars")
        print(f"  Metadata keys: {list(chunk.metadata.keys())}")
        print(f"  chunk_index: {chunk.metadata.get('chunk_index')}")
        print(f"  total_chunks: {chunk.metadata.get('total_chunks')}")
        print(f"  registry_id: {chunk.metadata.get('registry_id')}")
        print(f"  Text preview: {chunk.text[:100]}...")

    print("\n" + "="*80)
    print(f"FINAL COUNT: {len(chunks)} chunks created")
    print("="*80)

    # Check for duplicates
    unique_texts = set()
    duplicates = 0
    for chunk in chunks:
        if chunk.text in unique_texts:
            duplicates += 1
            print(f"WARNING: Duplicate text found in chunk!")
        unique_texts.add(chunk.text)

    print(f"\nDuplicate check: {duplicates} duplicates found out of {len(chunks)} chunks")

    return chunks

if __name__ == "__main__":
    chunks = test_chunking()
