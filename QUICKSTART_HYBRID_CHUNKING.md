# Quick Start: Hybrid Chunking Migration

**Time to complete**: 30-60 minutes
**Skill level**: Intermediate Python/RAG

---

## Step 1: Install Dependencies (5 min)

```bash
# Navigate to project root
cd c:\projects\aidocsbackend

# Activate virtual environment
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install hybrid chunking dependencies
pip install "docling-core[chunking]"
pip install transformers

# Verify installation
python -c "from docling_core.transforms.chunker.hybrid_chunker import HybridChunker; print('✅ Hybrid chunking available')"
```

---

## Step 2: Update Configuration (5 min)

### Add to `rag_indexer/.env`:

```bash
# Hybrid Chunking Settings
USE_HYBRID_CHUNKING=true
HYBRID_MAX_TOKENS=512
HYBRID_MERGE_PEERS=true
HYBRID_USE_CONTEXTUALIZE=false

# Tokenizer (HuggingFace recommended)
HYBRID_TOKENIZER=huggingface
HYBRID_TOKENIZER_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Update `rag_indexer/chunking_vectors/config.py`:

Add after line 55 (after `MIN_CHUNK_LENGTH`):

```python
# --- HYBRID CHUNKING SETTINGS ---
self.USE_HYBRID_CHUNKING = os.getenv("USE_HYBRID_CHUNKING", "false").lower() == "true"
self.HYBRID_MAX_TOKENS = int(os.getenv("HYBRID_MAX_TOKENS", str(self.CHUNK_SIZE)))
self.HYBRID_MERGE_PEERS = os.getenv("HYBRID_MERGE_PEERS", "true").lower() == "true"
self.HYBRID_USE_CONTEXTUALIZE = os.getenv("HYBRID_USE_CONTEXTUALIZE", "false").lower() == "true"
self.HYBRID_TOKENIZER = os.getenv("HYBRID_TOKENIZER", "huggingface")
self.HYBRID_TOKENIZER_MODEL = os.getenv("HYBRID_TOKENIZER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
```

Add after line 178 (after `get_chunk_settings()` method):

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

## Step 3: Add Hybrid Chunker Module (2 min)

The file `hybrid_chunker.py` is already created at:
```
rag_indexer/chunking_vectors/hybrid_chunker.py
```

**Verify it exists:**
```bash
ls rag_indexer/chunking_vectors/hybrid_chunker.py
# Should show the file
```

---

## Step 4: Update Chunk Helpers (10 min)

### Replace `create_and_filter_chunks_enhanced()` in `chunk_helpers.py`:

Open `rag_indexer/chunking_vectors/chunk_helpers.py` and find the function `create_and_filter_chunks_enhanced()`.

Replace it with the version from `chunk_helpers_hybrid.py`:

```bash
# The updated version is in:
# rag_indexer/chunking_vectors/chunk_helpers_hybrid.py

# Copy the function to chunk_helpers.py
```

**Or manually add this import at the top** of `chunk_helpers.py`:

```python
# Add after other imports
from chunking_vectors.hybrid_chunker import create_hybrid_chunker, is_hybrid_chunking_available
```

**Then update the function** (lines will vary, but look for `create_and_filter_chunks_enhanced`):

```python
def create_and_filter_chunks_enhanced(documents, node_parser, config, stats):
    # ... existing code ...

    # ADD THIS BLOCK at the beginning:
    hybrid_settings = config.get_hybrid_chunking_settings() if hasattr(config, 'get_hybrid_chunking_settings') else {'enabled': False}
    use_hybrid = hybrid_settings.get('enabled', False)

    if use_hybrid:
        logger.info("🧩 Using Hybrid Chunking (Docling HybridChunker)")
        try:
            if not is_hybrid_chunking_available():
                logger.error("❌ Hybrid chunking not available! Falling back.")
                use_hybrid = False
            else:
                chunker = create_hybrid_chunker(config)
                all_nodes = chunker.chunk_documents(documents)
                logger.info(f"   ✅ Created {len(all_nodes)} hybrid chunks")
        except Exception as e:
            logger.error(f"❌ Hybrid chunking failed: {e}, falling back")
            use_hybrid = False

    if not use_hybrid:
        # Existing SentenceSplitter code...
        logger.info("🧩 Using Legacy Chunking (SentenceSplitter)")
        all_nodes = []
        for doc in documents:
            nodes = node_parser.get_nodes_from_documents([doc])
            all_nodes.extend(nodes)

    # ... rest of the function stays the same ...
```

---

## Step 5: Test with Sample Data (10 min)

### Run the test script:

```bash
cd rag_indexer

# Create test directory with sample files
mkdir -p data/test_migration
cp data/markdown/*.md data/test_migration/ | head -10

# Run comparison test
python scripts/test_hybrid_chunking.py
```

**Expected output:**
```
🧪 HYBRID CHUNKING TEST & COMPARISON
================================================================================
📁 Loading test documents...
   ✅ Loaded 10 documents

🧪 Testing SentenceSplitter...
   ✅ Created 145 chunks in 0.32s
   Avg: 487 chars/chunk

🧪 Testing HybridChunker...
   ✅ Created 138 chunks in 0.58s
   Avg: 523 chars/chunk
   Chunk types: {'text': 120, 'table': 15, 'mixed': 3}

📊 CHUNKING COMPARISON RESULTS
================================================================================
🔢 Chunk Count:
   SentenceSplitter: 145
   HybridChunker:    138
   Difference:       -7 (-4.8%)

⏱️  Processing Time:
   SentenceSplitter: 0.32s
   HybridChunker:    0.58s
   Difference:       +0.26s (+81.3%)

✅ Test completed successfully!
```

---

## Step 6: Backup Database (5 min)

**Critical step before reindexing!**

```bash
# Set connection string
export SUPABASE_CONNECTION_STRING="your_connection_string"

# Backup vecs.documents table
pg_dump -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -t vecs.documents \
  -F c -f backups/vecs_documents_backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup
ls -lh backups/
```

---

## Step 7: Full Reindexing (15-30 min)

### Enable hybrid chunking:

```bash
# Edit rag_indexer/.env
USE_HYBRID_CHUNKING=true
```

### Clear existing index (optional):

```bash
# Only if you want a clean slate
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c "TRUNCATE vecs.documents;"
```

### Run indexer:

```bash
cd rag_indexer

# Run with progress logging
python indexer.py
```

**Monitor output for:**
- ✅ "Using Hybrid Chunking (Docling HybridChunker)"
- ✅ Chunk count per document
- ✅ Metadata enrichment (doc_items, chunk_type)
- ❌ Any errors (should fall back to SentenceSplitter if fails)

---

## Step 8: Validate Results (10 min)

### Check database:

```bash
# Count chunks
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c "SELECT COUNT(*) FROM vecs.documents;"

# Check metadata structure
psql -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c "SELECT metadata FROM vecs.documents LIMIT 1;" | jq
```

**Expected metadata (HybridChunker):**
```json
{
  "file_name": "document.md",
  "registry_id": "uuid-here",
  "chunking_method": "hybrid_docling",
  "chunk_type": "text",
  "doc_items": ["TEXT", "SECTION_HEADER"],
  "parent_heading": "Chapter 1"
}
```

### Test search in client_rag:

```bash
cd client_rag/scripts

# Run test query
python quick_search.py

# Should work without errors
# Results may be slightly different (better context)
```

---

## Step 9: Compare Quality (Optional)

### Metrics to check:

1. **Chunk count**: Should be within ±20% of original
2. **Search results**: Run same queries, compare relevance
3. **Table integrity**: Check that tables aren't split
4. **Performance**: Note indexing time (may be 1.5-2x slower)

### A/B Test:

```bash
# Keep backup of old index
# Reindex with USE_HYBRID_CHUNKING=true
# Compare search quality side-by-side
```

---

## Rollback (If Needed)

If something goes wrong:

### Step 1: Disable hybrid chunking

```bash
# Edit rag_indexer/.env
USE_HYBRID_CHUNKING=false
```

### Step 2: Restore database

```bash
# Restore from backup
pg_restore -h YOUR_HOST -U YOUR_USER -d YOUR_DB \
  -c -t vecs.documents \
  backups/vecs_documents_backup_YYYYMMDD_HHMMSS.dump
```

### Step 3: Reindex with SentenceSplitter

```bash
cd rag_indexer
python indexer.py
```

---

## Troubleshooting

### Issue: "Module 'docling_core' not found"

```bash
pip install "docling-core[chunking]"
```

### Issue: "Tokenizer model not found"

```bash
pip install transformers
# First run downloads model from HuggingFace
# Wait for download to complete
```

### Issue: Chunks missing registry_id

**Check:**
1. Is `registry_manager` passed to `markdown_loader.load_data()`?
2. Are documents in `document_registry` table?
3. Check logs for "registry enrichment" messages

### Issue: Hybrid chunking very slow

**Solutions:**
1. Reduce batch size: `PROCESSING_BATCH_SIZE=25`
2. Disable contextualize: `HYBRID_USE_CONTEXTUALIZE=false`
3. Use smaller tokenizer model

### Issue: Search broken in client_rag

**This should NOT happen** - hybrid chunking is compatible.

**Check:**
1. Metadata has `file_name` field
2. Metadata has `registry_id` field
3. UUID monkey patch is active (check logs)
4. Run: `python client_rag/scripts/analyze_chunks.py`

---

## Success Checklist

- ✅ Dependencies installed (`docling-core[chunking]`, `transformers`)
- ✅ Configuration updated (`.env`, `config.py`, `chunk_helpers.py`)
- ✅ Test passed (`test_hybrid_chunking.py`)
- ✅ Database backed up
- ✅ Reindexing completed without errors
- ✅ Chunks have correct metadata (`chunking_method=hybrid_docling`)
- ✅ Search works in `client_rag`
- ✅ No performance degradation (< 2x slower)

---

## Next Steps

### Optional Enhancements:

1. **Enable Contextualization** (better embeddings):
   ```bash
   HYBRID_USE_CONTEXTUALIZE=true
   ```
   Reindex to get heading hierarchy in chunks.

2. **Structural Filtering** in `client_rag`:
   - Filter by `chunk_type` (table, text, list)
   - Use `parent_heading` for context display
   - Boost table chunks for table queries

3. **Picture Description** (future):
   - After validating Hybrid Chunking quality
   - Replace OCR enhancer with Docling VLM
   - See `MIGRATION_HYBRID_CHUNKING.md` for details

---

## Support

**Documentation:**
- Full migration plan: `MIGRATION_HYBRID_CHUNKING.md`
- Docling docs: https://docling-project.github.io/docling/

**Testing:**
- Comparison script: `rag_indexer/scripts/test_hybrid_chunking.py`
- Validation scripts: `client_rag/scripts/`

**Rollback:**
- Database backup in `backups/`
- Disable with `USE_HYBRID_CHUNKING=false`

---

**Last Updated**: 2025-01-21
**Version**: 1.0
**Estimated Time**: 30-60 minutes
