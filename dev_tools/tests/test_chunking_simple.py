#!/usr/bin/env python3
import sys
sys.path.insert(0, 'rag_indexer')

import os
from dotenv import load_dotenv
load_dotenv('rag_indexer/.env')

# Import the exact function used in production
from chunking_vectors.chunk_helpers_hybrid import create_enhanced_chunks_hybrid
from chunking_vectors.config import Config
from llama_index.core import Document
from storage.storage_manager import SupabaseStorageManager
import json

print("="*80)
print("Testing Hybrid Chunking - Vehicle Registration Certificate")
print("="*80)

# Initialize config
config = Config()

# Download files
storage = SupabaseStorageManager()

print("\nDownloading files from Storage...")
md_path = storage.download_to_temp('markdown/processed/1761382324_Vehicle_Registration_Certificate.md')
json_path = storage.download_to_temp('json/processed/1761382324_Vehicle_Registration_Certificate.json')

# Read markdown
with open(md_path, 'r', encoding='utf-8') as f:
    md_content = f.read()

print(f"Markdown: {len(md_content)} chars")

# Create document
document = Document(
    text=md_content,
    metadata={
        'file_name': '1761382324_Vehicle_Registration_Certificate.md',
        'file_path': str(md_path),
        'json_path': str(json_path),
        'registry_id': 'aa24d13e-1e8d-422d-a1ab-608636de4906',
        'original_filename': 'Vehicle Registration Certificate.pdf'
    }
)

print(f"\nCalling create_enhanced_chunks_hybrid...")
print(f"Documents to process: 1")

chunks, report = create_enhanced_chunks_hybrid([document], config)

print(f"\n{'='*80}")
print(f"RESULT: {len(chunks)} chunks created")
print(f"{'='*80}")

for i, chunk in enumerate(chunks):
    print(f"\nChunk {i}:")
    print(f"  Text length: {len(chunk.text)} chars")
    print(f"  chunk_index: {chunk.metadata.get('chunk_index')}")
    print(f"  registry_id: {chunk.metadata.get('registry_id')}")
    print(f"  Preview: {chunk.text[:80]}...")

# Check for duplicates
texts = [c.text for c in chunks]
unique = set(texts)
print(f"\nDuplicate check: {len(texts)} total, {len(unique)} unique")
if len(texts) != len(unique):
    print(f"  WARNING: {len(texts) - len(unique)} duplicates found!")
