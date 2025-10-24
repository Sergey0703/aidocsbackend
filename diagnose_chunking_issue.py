#!/usr/bin/env python3
"""Diagnose why CVRT was chunked incorrectly"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / 'rag_indexer'))

load_dotenv('rag_indexer/.env')

from chunking_vectors.config import Config

config = Config()

print("\n" + "="*80)
print("CHUNKING CONFIGURATION DIAGNOSIS")
print("="*80 + "\n")

print("Configuration loaded from .env:")
print(f"  USE_HYBRID_CHUNKING: {config.USE_HYBRID_CHUNKING}")
print(f"  HYBRID_MAX_TOKENS: {config.HYBRID_MAX_TOKENS}")
print(f"  HYBRID_MERGE_PEERS: {config.HYBRID_MERGE_PEERS}")
print(f"  HYBRID_USE_CONTEXTUALIZE: {config.HYBRID_USE_CONTEXTUALIZE}")
print(f"  HYBRID_TOKENIZER: {config.HYBRID_TOKENIZER}")
print(f"  HYBRID_TOKENIZER_MODEL: {config.HYBRID_TOKENIZER_MODEL}")
print()

print("Fallback SentenceSplitter settings:")
print(f"  CHUNK_SIZE: {config.CHUNK_SIZE}")
print(f"  CHUNK_OVERLAP: {config.CHUNK_OVERLAP}")
print(f"  MIN_CHUNK_LENGTH: {config.MIN_CHUNK_LENGTH}")
print()

# Check if hybrid chunking is available
print("="*80)
print("HYBRID CHUNKING AVAILABILITY CHECK")
print("="*80 + "\n")

try:
    from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
    print("[+] Docling HybridChunker: AVAILABLE")
except ImportError as e:
    print(f"[-] Docling HybridChunker: NOT AVAILABLE")
    print(f"    Error: {e}")

try:
    from chunking_vectors.hybrid_chunker import is_hybrid_chunking_available
    available = is_hybrid_chunking_available()
    print(f"[+] Hybrid chunking wrapper available: {available}")
except ImportError as e:
    print(f"[-] Hybrid chunker wrapper: NOT AVAILABLE")
    print(f"    Error: {e}")

# Check the markdown_loader to see which chunker is being used
print()
print("="*80)
print("MARKDOWN LOADER CONFIGURATION")
print("="*80 + "\n")

try:
    from chunking_vectors.markdown_loader import MarkdownLoaderWithRegistry

    print("MarkdownLoaderWithRegistry class found.")
    print("Checking which chunking method is configured...")

    # Check the get_hybrid_chunking_settings method
    hybrid_settings = config.get_hybrid_chunking_settings()
    print(f"\nHybrid chunking settings from config:")
    for key, value in hybrid_settings.items():
        print(f"  {key}: {value}")

except ImportError as e:
    print(f"[-] Error importing MarkdownLoader: {e}")

print()
print("="*80)
print("PROBLEM ANALYSIS")
print("="*80 + "\n")

if config.USE_HYBRID_CHUNKING:
    print("[*] Hybrid chunking is ENABLED in .env")
    try:
        from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
        print("[*] HybridChunker is available")
        print()
        print("POSSIBLE CAUSES:")
        print("  1. CVRT document was indexed BEFORE hybrid chunking was enabled")
        print("  2. Markdown fallback was triggered (JSON file missing during indexing)")
        print("  3. HybridChunker failed and fell back to SentenceSplitter")
        print("  4. Indexing pipeline didn't reload config properly")
        print()
        print("RECOMMENDATION:")
        print("  Delete and re-index the CVRT document to use HybridChunker")
    except ImportError:
        print("[-] HybridChunker is NOT available")
        print()
        print("PROBLEM: Hybrid chunking is enabled but dependencies are missing!")
        print("Solution: Install with: pip install 'docling-core[chunking]'")
else:
    print("[!] Hybrid chunking is DISABLED in .env")
    print()
    print("PROBLEM: USE_HYBRID_CHUNKING=false")
    print("Solution: Set USE_HYBRID_CHUNKING=true in rag_indexer/.env")

print()
