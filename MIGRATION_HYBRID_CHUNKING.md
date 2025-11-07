# Migration Plan: Hybrid Chunking Integration

**Date:** 2025-01-21
**Target:** Migrate from SentenceSplitter to Docling HybridChunker
**Scope:** `rag_indexer/` only (Part 2: Chunking & Vectors)
**Impact:** `client_rag/` requires minimal changes (95% compatible)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Prerequisites](#prerequisites)
3. [Migration Timeline](#migration-timeline)
4. [Detailed Implementation Steps](#detailed-implementation-steps)
5. [Code Changes](#code-changes)
6. [Testing Strategy](#testing-strategy)
7. [Rollback Plan](#rollback-plan)
8. [Post-Migration Validation](#post-migration-validation)

---

## Executive Summary

### Objective
Replace `SentenceSplitter` (LlamaIndex) with `HybridChunker` (Docling) for improved document chunking quality through structure-aware splitting.

### Key Benefits
- **Better structure preservation**: Tables, lists, and headings stay intact
- **Contextual enrichment**: Automatic heading hierarchy in chunks
- **Adaptive chunking**: Token-aware splitting based on document structure
- **Table integrity**: Tables no longer split mid-content
- **Metadata richness**: doc_items, chunk_type, parent_heading

### Impact Assessment
| Component | Change Level | Risk | Testing Required |
|-----------|--------------|------|------------------|
| `rag_indexer/chunking_vectors/` | **High** | Medium | ✅ Critical |
| `rag_indexer/indexer.py` | **Medium** | Low | ✅ Required |
| `client_rag/retrieval/` | **Minimal** | Very Low | ⚠️ Verification |
| `vecs.documents` schema | **None** | None | ✅ Compatibility check |

### Estimated Timeline
- **Planning & Prep**: 2 hours
- **Implementation**: 4-6 hours
- **Testing**: 2-3 hours
- **Validation**: 1-2 hours
- **Total**: 1-2 days (with buffer)

---

## Prerequisites

### 1. Dependencies Installation

```bash
# Install docling-core with chunking support
pip install "docling-core[chunking]"

# For HuggingFace tokenizer (recommended for Gemini)
pip install transformers

# For OpenAI tokenizer (alternative)
# pip install "docling-core[chunking-openai]" tiktoken
```

### 2. Environment Variables (`.env`)

```bash
# Add these new settings to rag_indexer/.env

# Hybrid Chunking Settings
USE_HYBRID_CHUNKING=true  # Toggle between SentenceSplitter and HybridChunker
HYBRID_MAX_TOKENS=512     # Max tokens per chunk (matching current CHUNK_SIZE)
HYBRID_MERGE_PEERS=true   # Merge sibling paragraphs in same section
HYBRID_USE_CONTEXTUALIZE=false  # Use enriched context for embeddings (optional)

# Tokenizer Settings
HYBRID_TOKENIZER=huggingface  # Options: huggingface, openai
HYBRID_TOKENIZER_MODEL=sentence-transformers/all-MiniLM-L6-v2  # HF model ID
# HYBRID_TOKENIZER_MODEL=gpt-4o  # For OpenAI tokenizer

# Backward compatibility (keep existing)
CHUNK_SIZE=512
CHUNK_OVERLAP=128
```

### 3. Backup Current Database

```bash
# Backup vecs.documents table
pg_dump -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -t vecs.documents \
  -F c -f vecs_documents_backup_$(date +%Y%m%d_%H%M%S).dump

# Or SQL export
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c "COPY (SELECT * FROM vecs.documents) TO STDOUT CSV HEADER" \
  > vecs_documents_backup_$(date +%Y%m%d_%H%M%S).csv
```

### 4. Create Test Dataset

```bash
# Copy 10-20 markdown files to test directory
mkdir -p rag_indexer/data/test_migration
cp rag_indexer/data/markdown/*.md rag_indexer/data/test_migration/ | head -20
```

---

## Migration Timeline

### Phase 1: Preparation (Day 1 Morning)
- ✅ Install dependencies (`docling-core[chunking]`, `transformers`)
- ✅ Backup database (`vecs.documents`)
- ✅ Create test dataset (10-20 markdown files)
- ✅ Document current metrics (chunk count, avg size, search quality)

### Phase 2: Implementation (Day 1 Afternoon)
- ✅ Create `hybrid_chunker.py` module
- ✅ Update `config.py` with hybrid settings
- ✅ Modify `markdown_loader.py` for DoclingDocument support
- ✅ Update `chunk_helpers.py` for hybrid chunks
- ✅ Add backward compatibility flag

### Phase 3: Testing (Day 1 Evening / Day 2 Morning)
- ✅ Unit tests for `hybrid_chunker.py`
- ✅ Integration test with test dataset
- ✅ Metadata validation (registry_id, file_name, etc.)
- ✅ Embedding generation test
- ✅ Database save test

### Phase 4: Validation (Day 2 Afternoon)
- ✅ Full reindexing with hybrid chunking
- ✅ Chunk count comparison (before/after)
- ✅ Search quality A/B test (`client_rag`)
- ✅ Metadata structure validation
- ✅ Performance metrics (time, memory)

### Phase 5: Deployment (Day 2 Evening)
- ✅ Switch `USE_HYBRID_CHUNKING=true` in production `.env`
- ✅ Run full reindexing
- ✅ Monitor logs for errors
- ✅ Verify search quality in `client_rag`

---

## Detailed Implementation Steps

### Step 1: Create `hybrid_chunker.py` Module

**Location**: `rag_indexer/chunking_vectors/hybrid_chunker.py`

**Purpose**:
- Wrapper around Docling HybridChunker
- Convert markdown to DoclingDocument
- Extract chunks with metadata
- Maintain compatibility with LlamaIndex nodes

**Key Functions**:
1. `create_hybrid_chunker(config)` - Factory function
2. `HybridChunkerWrapper.chunk_documents(docs)` - Main chunking method
3. `_markdown_to_docling_document(md_content)` - Conversion helper
4. `_docling_chunk_to_llamaindex_node(chunk)` - Format converter

See [Code Changes](#code-changes) section for full implementation.

---

### Step 2: Update `config.py`

**Changes**:
- Add hybrid chunking settings
- Maintain backward compatibility
- Validate tokenizer configuration

```python
# Add to config.py

# --- HYBRID CHUNKING SETTINGS (NEW) ---
self.USE_HYBRID_CHUNKING = os.getenv("USE_HYBRID_CHUNKING", "false").lower() == "true"
self.HYBRID_MAX_TOKENS = int(os.getenv("HYBRID_MAX_TOKENS", "512"))
self.HYBRID_MERGE_PEERS = os.getenv("HYBRID_MERGE_PEERS", "true").lower() == "true"
self.HYBRID_USE_CONTEXTUALIZE = os.getenv("HYBRID_USE_CONTEXTUALIZE", "false").lower() == "true"
self.HYBRID_TOKENIZER = os.getenv("HYBRID_TOKENIZER", "huggingface")
self.HYBRID_TOKENIZER_MODEL = os.getenv("HYBRID_TOKENIZER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def get_hybrid_chunking_settings(self):
    """Return hybrid chunking settings as a dictionary"""
    return {
        'enabled': self.USE_HYBRID_CHUNKING,
        'max_tokens': self.HYBRID_MAX_TOKENS,
        'merge_peers': self.HYBRID_MERGE_PEERS,
        'use_contextualize': self.HYBRID_USE_CONTEXTUALIZE,
        'tokenizer': self.HYBRID_TOKENIZER,
        'tokenizer_model': self.HYBRID_TOKENIZER_MODEL,
    }
```

---

### Step 3: Modify `markdown_loader.py`

**Changes**:
- Add DoclingDocument support (optional, for advanced features)
- Keep current LlamaIndex Document format (for backward compatibility)
- Add metadata for chunk_type tracking

**Option A: Minimal Changes (Recommended)**
```python
# NO CHANGES NEEDED to markdown_loader.py
# HybridChunker can work with plain markdown text
# Conversion happens in hybrid_chunker.py
```

**Option B: Full DoclingDocument Integration (Advanced)**
```python
# Add to markdown_loader.py if you want richer metadata

def _create_docling_document_from_markdown(self, file_path: str, content: str):
    """Create DoclingDocument from markdown (for HybridChunker)"""
    from docling_core.types.doc.document import DoclingDocument

    # Simple conversion: load markdown as DoclingDocument
    doc = DoclingDocument.load_from_markdown_string(content)

    # Enrich with file metadata
    doc.metadata['file_path'] = str(file_path)
    doc.metadata['file_name'] = Path(file_path).name

    return doc
```

---

### Step 4: Update `chunk_helpers.py`

**Changes**:
- Add hybrid chunking path
- Maintain SentenceSplitter fallback
- Preserve all metadata

```python
# Update create_and_filter_chunks_enhanced()

def create_and_filter_chunks_enhanced(documents, node_parser, config, stats):
    """
    Create and filter chunks from documents - UPDATED for hybrid chunking support
    """
    from chunking_vectors.hybrid_chunker import create_hybrid_chunker

    # Choose chunker based on config
    if config.USE_HYBRID_CHUNKING:
        print("🧩 Using Hybrid Chunking (Docling HybridChunker)")
        chunker = create_hybrid_chunker(config)
        all_nodes = chunker.chunk_documents(documents)
    else:
        print("🧩 Using Legacy Chunking (SentenceSplitter)")
        all_nodes = []
        for doc in documents:
            nodes = node_parser.get_nodes_from_documents([doc])
            all_nodes.extend(nodes)

    # Rest of the function stays the same (filtering, validation, etc.)
    # ...
```

---

### Step 5: Update `indexer.py`

**Changes**:
- Pass config to chunk creation
- Add hybrid chunking status to reports

```python
# In initialize_components()

if config.USE_HYBRID_CHUNKING:
    print("   ✅ Chunking: Hybrid (Docling HybridChunker)")
    # No need for node_parser in this case
    node_parser = None
else:
    print("   ✅ Chunking: Legacy (SentenceSplitter)")
    chunk_settings = config.get_chunk_settings()
    node_parser = SentenceSplitter(
        chunk_size=chunk_settings['chunk_size'],
        chunk_overlap=chunk_settings['chunk_overlap'],
        # ...
    )
```

---

## Code Changes

### File 1: `hybrid_chunker.py` (NEW)

**Full implementation** - see separate code file below.

---

### File 2: `config.py` (UPDATE)

**Add after line 55** (after `MIN_CHUNK_LENGTH`):

```python
# --- HYBRID CHUNKING SETTINGS ---
self.USE_HYBRID_CHUNKING = os.getenv("USE_HYBRID_CHUNKING", "false").lower() == "true"
self.HYBRID_MAX_TOKENS = int(os.getenv("HYBRID_MAX_TOKENS", str(self.CHUNK_SIZE)))
self.HYBRID_MERGE_PEERS = os.getenv("HYBRID_MERGE_PEERS", "true").lower() == "true"
self.HYBRID_USE_CONTEXTUALIZE = os.getenv("HYBRID_USE_CONTEXTUALIZE", "false").lower() == "true"
self.HYBRID_TOKENIZER = os.getenv("HYBRID_TOKENIZER", "huggingface")
self.HYBRID_TOKENIZER_MODEL = os.getenv("HYBRID_TOKENIZER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
```

**Add new method** (after line 178):

```python
def get_hybrid_chunking_settings(self):
    """Return hybrid chunking settings as a dictionary"""
    return {
        'enabled': self.USE_HYBRID_CHUNKING,
        'max_tokens': self.HYBRID_MAX_TOKENS,
        'merge_peers': self.HYBRID_MERGE_PEERS,
        'use_contextualize': self.HYBRID_USE_CONTEXTUALIZE,
        'tokenizer': self.HYBRID_TOKENIZER,
        'tokenizer_model': self.HYBRID_TOKENIZER_MODEL,
    }
```

---

### File 3: `chunk_helpers.py` (UPDATE)

**Replace `create_and_filter_chunks_enhanced()` function**:

See separate code implementation below.

---

## Testing Strategy

### 1. Unit Tests

```python
# tests/test_hybrid_chunker.py

import pytest
from chunking_vectors.hybrid_chunker import create_hybrid_chunker
from chunking_vectors.config import Config
from llama_index.core import Document

def test_hybrid_chunker_initialization():
    """Test hybrid chunker initialization"""
    config = Config()
    config.USE_HYBRID_CHUNKING = True
    config.HYBRID_MAX_TOKENS = 512

    chunker = create_hybrid_chunker(config)
    assert chunker is not None
    assert chunker.chunker is not None

def test_chunk_simple_markdown():
    """Test chunking simple markdown"""
    config = Config()
    config.USE_HYBRID_CHUNKING = True

    chunker = create_hybrid_chunker(config)

    # Create test document
    test_md = """
    # Chapter 1

    This is a test paragraph.

    ## Section 1.1

    Another paragraph here.
    """

    doc = Document(text=test_md, metadata={'file_name': 'test.md'})
    nodes = chunker.chunk_documents([doc])

    assert len(nodes) > 0
    assert all(hasattr(n, 'metadata') for n in nodes)
    assert all('file_name' in n.metadata for n in nodes)

def test_metadata_preservation():
    """Test that metadata is preserved through chunking"""
    config = Config()
    config.USE_HYBRID_CHUNKING = True

    chunker = create_hybrid_chunker(config)

    # Document with registry_id
    doc = Document(
        text="Test content",
        metadata={
            'file_name': 'test.md',
            'registry_id': '550e8400-e29b-41d4-a716-446655440000'
        }
    )

    nodes = chunker.chunk_documents([doc])

    assert len(nodes) > 0
    assert nodes[0].metadata.get('registry_id') == '550e8400-e29b-41d4-a716-446655440000'
```

### 2. Integration Tests

```bash
# Run test indexing with hybrid chunking
cd rag_indexer

# Set test environment
export USE_HYBRID_CHUNKING=true
export DOCUMENTS_DIR="./data/test_migration"

# Run indexer
python indexer.py

# Verify chunks in database
python -c "
import psycopg2
conn = psycopg2.connect(os.getenv('SUPABASE_CONNECTION_STRING'))
cur = conn.cursor()
cur.execute('SELECT COUNT(*), AVG(LENGTH(metadata::text)) FROM vecs.documents')
print(cur.fetchone())
"
```

### 3. A/B Comparison

```python
# scripts/compare_chunking_methods.py

import os
from chunking_vectors.config import Config
from chunking_vectors.markdown_loader import MarkdownLoader
from llama_index.core.node_parser import SentenceSplitter
from chunking_vectors.hybrid_chunker import create_hybrid_chunker

def compare_chunking_methods():
    """Compare SentenceSplitter vs HybridChunker"""

    config = Config()

    # Load test documents
    loader = MarkdownLoader(
        input_dir="./data/test_migration",
        recursive=False,
        config=config
    )
    docs, _ = loader.load_data()

    print(f"Loaded {len(docs)} documents for comparison\n")

    # Method 1: SentenceSplitter
    sentence_splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=128
    )
    sentence_chunks = []
    for doc in docs:
        sentence_chunks.extend(sentence_splitter.get_nodes_from_documents([doc]))

    # Method 2: HybridChunker
    config.USE_HYBRID_CHUNKING = True
    hybrid_chunker = create_hybrid_chunker(config)
    hybrid_chunks = hybrid_chunker.chunk_documents(docs)

    # Compare results
    print("=" * 60)
    print("CHUNKING METHOD COMPARISON")
    print("=" * 60)
    print(f"SentenceSplitter chunks: {len(sentence_chunks)}")
    print(f"HybridChunker chunks: {len(hybrid_chunks)}")
    print(f"Difference: {len(hybrid_chunks) - len(sentence_chunks)}")

    # Average chunk size
    sentence_avg = sum(len(c.text) for c in sentence_chunks) / len(sentence_chunks)
    hybrid_avg = sum(len(c.text) for c in hybrid_chunks) / len(hybrid_chunks)

    print(f"\nAverage chunk size:")
    print(f"  SentenceSplitter: {sentence_avg:.0f} chars")
    print(f"  HybridChunker: {hybrid_avg:.0f} chars")

    # Metadata comparison
    sentence_meta_keys = set()
    for c in sentence_chunks:
        sentence_meta_keys.update(c.metadata.keys())

    hybrid_meta_keys = set()
    for c in hybrid_chunks:
        hybrid_meta_keys.update(c.metadata.keys())

    print(f"\nMetadata keys:")
    print(f"  SentenceSplitter: {sorted(sentence_meta_keys)}")
    print(f"  HybridChunker: {sorted(hybrid_meta_keys)}")
    print(f"  New keys in Hybrid: {sorted(hybrid_meta_keys - sentence_meta_keys)}")

    print("=" * 60)

if __name__ == "__main__":
    compare_chunking_methods()
```

---

## Rollback Plan

### Immediate Rollback (< 1 hour)

If critical issues occur during testing:

**Step 1: Disable Hybrid Chunking**
```bash
# Edit rag_indexer/.env
USE_HYBRID_CHUNKING=false
```

**Step 2: Restore Database (if needed)**
```bash
# Restore from backup
pg_restore -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -t vecs.documents \
  vecs_documents_backup_YYYYMMDD_HHMMSS.dump

# Or from CSV
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c "TRUNCATE vecs.documents"
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c "\COPY vecs.documents FROM 'vecs_documents_backup_YYYYMMDD_HHMMSS.csv' CSV HEADER"
```

**Step 3: Reindex with SentenceSplitter**
```bash
cd rag_indexer
python indexer.py
```

### Code Rollback

**Option 1: Git Revert**
```bash
git stash  # Save local changes
git checkout COMMIT_HASH_BEFORE_MIGRATION
```

**Option 2: Selective Rollback**
```bash
# Keep hybrid_chunker.py but disable in config
# Keep all changes for future retry
# Just toggle USE_HYBRID_CHUNKING=false
```

---

## Post-Migration Validation

### 1. Database Integrity

```sql
-- Check chunk count
SELECT COUNT(*) as total_chunks FROM vecs.documents;

-- Check metadata structure
SELECT
    COUNT(*) as count,
    jsonb_object_keys(metadata) as key
FROM vecs.documents
GROUP BY key
ORDER BY count DESC;

-- Check registry_id integrity
SELECT COUNT(*) as chunks_with_registry
FROM vecs.documents
WHERE metadata->>'registry_id' IS NOT NULL;

-- Compare with document_registry
SELECT
    dr.status,
    COUNT(DISTINCT d.metadata->>'registry_id') as chunks_count
FROM vecs.document_registry dr
LEFT JOIN vecs.documents d ON dr.id::text = d.metadata->>'registry_id'
GROUP BY dr.status;
```

### 2. Search Quality Test

```bash
# Run quick search tests
cd client_rag/scripts
python quick_search.py

# Expected: Similar or better results than before
# Check: No errors in retrieval
# Verify: Metadata compatibility (file_name, registry_id)
```

### 3. Performance Metrics

```python
# Compare before/after metrics

BEFORE (SentenceSplitter):
- Total chunks: XXXX
- Avg chunk size: XXX chars
- Indexing time: XX minutes
- Search quality: X.XX precision

AFTER (HybridChunker):
- Total chunks: XXXX
- Avg chunk size: XXX chars
- Indexing time: XX minutes
- Search quality: X.XX precision
```

### 4. Metadata Validation

```python
# client_rag/scripts/validate_hybrid_metadata.py

import psycopg2
import os
import json

def validate_hybrid_metadata():
    conn = psycopg2.connect(os.getenv('SUPABASE_CONNECTION_STRING'))
    cur = conn.cursor()

    # Get sample chunk
    cur.execute("SELECT metadata FROM vecs.documents LIMIT 1")
    metadata = cur.fetchone()[0]

    print("Sample metadata structure:")
    print(json.dumps(metadata, indent=2))

    # Validate required fields
    required_fields = ['file_name', 'registry_id']
    for field in required_fields:
        cur.execute(f"""
            SELECT COUNT(*)
            FROM vecs.documents
            WHERE metadata->>'{field}' IS NOT NULL
        """)
        count = cur.fetchone()[0]
        print(f"✅ {field}: {count} chunks")

    # Check new hybrid fields
    hybrid_fields = ['doc_items', 'chunk_type', 'parent_heading']
    for field in hybrid_fields:
        cur.execute(f"""
            SELECT COUNT(*)
            FROM vecs.documents
            WHERE metadata->>'{field}' IS NOT NULL
        """)
        count = cur.fetchone()[0]
        if count > 0:
            print(f"🆕 {field}: {count} chunks (NEW)")

if __name__ == "__main__":
    validate_hybrid_metadata()
```

---

## Success Criteria

Migration is considered successful when:

- ✅ All tests pass without errors
- ✅ Chunk count within expected range (±20% of original)
- ✅ Search quality is maintained or improved
- ✅ No errors in `client_rag` retrieval
- ✅ All chunks have `registry_id` and `file_name` metadata
- ✅ Database integrity checks pass
- ✅ Performance is acceptable (< 2x slower than SentenceSplitter)

---

## Next Steps After Migration

### Optional Enhancements

1. **Use Contextualized Embeddings**
   - Enable `HYBRID_USE_CONTEXTUALIZE=true`
   - Embeddings include heading hierarchy
   - Better semantic search quality

2. **Structural Filtering in `client_rag`**
   - Add `chunk_type` filtering (table, text, mixed)
   - Use `parent_heading` for context display
   - Boost table chunks for table queries

3. **Picture Description Integration** (Future)
   - After validating Hybrid Chunking quality
   - Replace OCR enhancer with Docling VLM
   - See separate migration plan

---

## Support & Troubleshooting

### Common Issues

**Issue 1: "Module 'docling_core' not found"**
```bash
pip install "docling-core[chunking]"
```

**Issue 2: "Tokenizer model not found"**
```bash
pip install transformers
# Or set different model:
export HYBRID_TOKENIZER_MODEL="sentence-transformers/all-MiniLM-L6-v2"
```

**Issue 3: Chunks missing registry_id**
```python
# Check markdown_loader enrichment
# Verify registry_manager is passed to loader.load_data()
```

**Issue 4: Hybrid chunking slower than expected**
```bash
# Reduce batch size
export PROCESSING_BATCH_SIZE=25
# Or disable contextualize
export HYBRID_USE_CONTEXTUALIZE=false
```

---

## Contact & Resources

- **Docling Documentation**: https://docling-project.github.io/docling/
- **HybridChunker Examples**: https://docling-project.github.io/docling/examples/hybrid_chunking
- **LlamaIndex Docs**: https://docs.llamaindex.ai/

---

**Last Updated**: 2025-01-21
**Version**: 1.0
**Status**: Ready for Implementation
