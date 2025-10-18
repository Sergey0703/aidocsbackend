# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready RAG (Retrieval-Augmented Generation) system specializing in vehicle documentation management with intelligent hybrid search. The system processes raw documents through a two-stage pipeline and provides semantic + database search capabilities via a FastAPI backend.

**Key Technology Stack:**
- **Document Processing**: Docling (PDF/DOCX/PPTX → Markdown)
- **Vector Embeddings**: Google Gemini API (text-embedding-004, 768D)
- **LLM Operations**: Google Gemini API (gemini-pro)
- **Vector Database**: Supabase PostgreSQL with pgvector extension
- **RAG Framework**: LlamaIndex (chunking, embeddings, retrieval)
- **Backend API**: FastAPI (located in `run_api.py` → `streamlit-rag/api/`)
- **Database Schema**: Vehicle registry with document tracking

## Project Structure

The codebase is organized into two main directories:

### 1. `rag_indexer/` - Document Indexing Pipeline
Two-stage document processing pipeline:

**Part 1: Document Conversion (Docling)**
- `docling_processor/` - Document conversion engine
  - `document_converter.py` - Converts raw files to markdown
  - `document_scanner.py` - Scans and filters documents
  - `metadata_extractor.py` - Extracts VRN, dates from documents
  - `config_docling.py` - Docling-specific configuration

**Part 2: Vector Indexing (LlamaIndex + Gemini)**
- `chunking_vectors/` - Chunking and embedding modules
  - `config.py` - Embedding and chunking configuration
  - `markdown_loader.py` - Loads markdown with registry enrichment
  - `embedding_processor.py` - Gemini API embedding generation
  - `batch_processor.py` - Batch processing with rate limiting
  - `database_manager.py` - Vector database operations
  - `registry_manager.py` - **Document registry tracking** (links docs to vehicles)
  - `incremental_indexer.py` - Incremental processing support

**Entry Points:**
- `indexer.py` - Main indexing script (Part 2 only: markdown → vectors)
- `process_documents.py` - Document conversion script (Part 1 only: raw → markdown)
- `pipeline.py` - Complete pipeline orchestrator (Part 1 + Part 2)

### 2. `streamlit-rag/` - Query & Retrieval API
Production RAG query system with hybrid search:

- `config/settings.py` - **Main configuration class** with hybrid search settings
- `query_processing/` - Query analysis modules
  - `entity_extractor.py` - Multi-method entity extraction (LLM/regex/SpaCy)
  - `query_rewriter.py` - Query expansion and simplification
- `retrieval/` - Hybrid retrieval system
  - `multi_retriever.py` - **Core retrieval logic** (vector + database search)
  - `results_fusion.py` - Result merging and ranking
- `api/` - FastAPI application (routes, models, core)
- `utils/` - Helper utilities (Excel export, encoding fixes)

## Database Schema

The system uses a **three-table architecture** in the `vecs` schema:

1. **`vecs.vehicles`** - Vehicle master registry
   - Tracks registration numbers, VIN, insurance/tax/NCT expiry dates
   - Links to current driver (auth.users)

2. **`vecs.document_registry`** - Document master table
   - Links documents to vehicles (optional)
   - Tracks document type (insurance, NCT, service records, etc.)
   - Stores processing status (pending_assignment → processed)
   - Holds extracted metadata (VRN, dates) in JSONB
   - Tracks both raw file path and markdown path

3. **`vecs.documents`** - Vector chunks for RAG
   - **IMPORTANT**: `id` is TEXT (not UUID) for vecs library compatibility
   - Foreign key to `document_registry` (registry_id UUID NOT NULL)
   - Contains 768D embeddings (Gemini text-embedding-004)
   - Metadata stored as JSONB

**Critical Constraint**: All chunks MUST have a valid `registry_id` linking to `document_registry`. Documents without registry entries will fail to index.

## Development Workflow

### Common Commands

**Environment Setup:**
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Document Processing Pipeline:**
```bash
# Full pipeline (convert + index)
cd rag_indexer
python pipeline.py

# Incremental mode (only new/modified files)
python pipeline.py --incremental

# Part 1 only: Convert documents to markdown
python process_documents.py
python process_documents.py --incremental

# Part 2 only: Index markdown to vectors
python indexer.py
# Set INCREMENTAL_MODE=true in .env for incremental indexing
```

**Running the API:**
```bash
# From project root
python run_api.py

# API will be available at http://0.0.0.0:8000
# Points to: streamlit-rag/api/main.py (FastAPI app)
```

**Testing & Scripts:**
```bash
cd streamlit-rag/scripts

# Quick search test
python quick_search.py

# Analyze chunks in database
python analyze_chunks.py

# Search by file name
python search_file_by_name.py
```

### Configuration Files

**Indexing Configuration:**
- `rag_indexer/chunking_vectors/config.py` - Controls chunking, embedding, batch processing
- `rag_indexer/docling_processor/config_docling.py` - Docling conversion settings
- `rag_indexer/.env` - Database connection, API keys, directories

**API Configuration:**
- `streamlit-rag/config/settings.py` - **Primary configuration** for hybrid search
- `streamlit-rag/.env` - API keys, connection strings

**Key Environment Variables:**
```bash
# Required for both indexer and API
SUPABASE_CONNECTION_STRING="postgresql://..."
GEMINI_API_KEY="your-api-key"

# Indexer-specific
RAW_DOCUMENTS_DIR="path/to/raw/docs"
MARKDOWN_OUTPUT_DIR="path/to/markdown"
TABLE_NAME="documents"
EMBED_MODEL="text-embedding-004"
EMBED_DIM="768"

# Optional
INCREMENTAL_MODE="true"  # For incremental indexing
GEMINI_REQUEST_RATE_LIMIT="10"  # Requests per second
```

## Architecture Details

### Hybrid Search System

The retrieval system implements a **three-strategy hybrid approach**:

1. **Database Search** (`DatabaseRetriever`)
   - Exact phrase matching with SQL LIKE queries
   - Flexible term search with OR conditions
   - Direct metadata search (file names, extracted VRNs)
   - High relevance scoring for exact matches

2. **Vector Search** (`LlamaIndexRetriever`)
   - Semantic similarity using Gemini embeddings
   - Adaptive similarity thresholds based on query type
   - Smart content validation and filtering
   - Entity-aware search parameters

3. **Fallback Search**
   - Activates when primary strategies fail
   - Relaxed parameters for broader recall
   - Database fallback with more lenient thresholds

**Search Strategy Selection:**
- Person/entity queries → Database priority
- Complex semantic queries → Vector priority
- Unknown queries → Balanced hybrid approach

**Fusion & Ranking:**
- Deduplicate by filename
- Apply source-aware weights (DB results weighted higher for exact matches)
- Boost exact entity matches in content
- Hybrid scoring combines similarity + match type

### Document Processing Workflow

**Stage 1: Conversion (Docling)**
1. Scan `RAW_DOCUMENTS_DIR` for PDF/DOCX/PPTX files
2. Extract metadata (VRN, dates) using regex patterns
3. Convert to markdown with document structure preservation
4. Save to `MARKDOWN_OUTPUT_DIR` with metadata JSON
5. Create entries in `vecs.document_registry` with status='pending_indexing'

**Stage 2: Indexing (LlamaIndex)**
1. Load markdown files from `MARKDOWN_OUTPUT_DIR`
2. **Enrich with registry_id** from `document_registry` (critical step!)
3. Chunk using SentenceSplitter (configurable size/overlap)
4. Filter invalid chunks (too short, low quality)
5. Generate embeddings via Gemini API (with rate limiting)
6. Save to `vecs.documents` with registry_id foreign key
7. Update `document_registry` status to 'processed'

**Incremental Mode:**
- Tracks file modification times in database
- Skips already-processed files
- Removes deleted files from database
- Significantly faster for large document sets

### Registry Manager Integration

The `registry_manager.py` module is critical for database integrity:

**Key Responsibilities:**
- Creates/updates `document_registry` entries
- Links markdown files to registry records via file path
- Enriches document metadata with `registry_id` before chunking
- Updates document status throughout pipeline
- Handles vehicle assignment (manual or automatic)

**Workflow:**
1. When markdown is loaded, lookup by `markdown_file_path`
2. If registry entry exists, inject `registry_id` into document metadata
3. During chunking, `registry_id` propagates to all chunks
4. When saving chunks, enforce foreign key constraint to registry
5. After successful indexing, update status to 'processed'

**Why This Matters:**
- Enables document-to-vehicle linkage
- Supports document lifecycle tracking
- Allows querying "all docs for vehicle X"
- Prevents orphaned chunks in database

### Entity Extraction Pipeline

Multi-method entity extraction with async support:

1. **LLM Extraction** (Gemini gemini-pro)
   - Prompt-based entity extraction
   - High confidence for clean extractions
   - Handles natural language queries

2. **Regex Extraction**
   - Pattern matching for names, VRNs
   - Fast, deterministic fallback
   - Good for structured queries

3. **SpaCy NER** (optional)
   - Named entity recognition
   - Good for person names
   - Requires `en_core_web_sm` model

**Fallback Strategy:**
- Try LLM first (if confidence > 0.7, use immediately)
- Fall back to SpaCy
- Final fallback to regex
- Return best result across all methods

### UUID Compatibility Fix

**Problem**: The `vecs` library returns UUID objects that cause serialization issues in FastAPI.

**Solution**: Monkey patch in `multi_retriever.py`:
```python
_original_query = vecs.Collection.query

def _patched_query(self, *args, **kwargs):
    results = _original_query(self, *args, **kwargs)
    # Convert UUID metadata to strings
    for item in results:
        if hasattr(item, 'metadata'):
            for key, value in item.metadata.items():
                if isinstance(value, uuid.UUID):
                    item.metadata[key] = str(value)
    return results

vecs.Collection.query = _patched_query
```

Applied at module load time in `multi_retriever.py:22-43`.

## Development Guidelines

### Adding New Document Types

1. Update `document_type` enum in schema (README.md shows SQL)
2. Add extraction patterns in `metadata_extractor.py`
3. Update vehicle assignment logic if needed
4. Test conversion → indexing → retrieval flow

### Modifying Search Behavior

Primary configuration in `streamlit-rag/config/settings.py`:
- `SearchConfig` - Thresholds, weights, strategy selection
- `known_entities` - Entity-specific search parameters
- Weights for hybrid fusion (database_result_weight, vector_result_weight)

### Debugging Indexing Issues

**Check these in order:**
1. Verify `.env` has correct `SUPABASE_CONNECTION_STRING` and `GEMINI_API_KEY`
2. Ensure markdown files exist in `MARKDOWN_OUTPUT_DIR`
3. Check `document_registry` has entries for your markdown files
4. Verify `registry_id` is present in document metadata (logs show this)
5. Review batch processing logs for embedding errors
6. Check database constraints (foreign keys, NOT NULL)

**Common Issues:**
- "Chunks without registry_id" → Check `registry_manager` enrichment step
- "Embedding API errors" → Check Gemini API quota/rate limits
- "No markdown files found" → Run Part 1 (process_documents.py) first
- "Database constraint violation" → Missing registry entries

### Testing Search Quality

Use `streamlit-rag/scripts/quick_search.py` for rapid iteration:
```python
# Modify query in script
query = "John Nolan"  # or VRN like "191-D-12345"

# Run search
python quick_search.py

# Observe:
# - Which retrieval strategies activated
# - Number of results from each source
# - Similarity scores and rankings
# - Metadata (source_method, match_type)
```

## Performance Considerations

**Gemini API Rate Limiting:**
- Default: 10 requests/second (configured in .env)
- Batch processor handles rate limiting automatically
- Embedding generation is sequential (not parallel)
- Large document sets may take hours to process

**Database Query Optimization:**
- Indexes on `file_path`, `vehicle_id`, `status` in `document_registry`
- HNSW index on vector column for fast similarity search
- GIN index on JSONB metadata for fast JSON queries

**Incremental Mode Benefits:**
- Skip unchanged files (90%+ time savings for updates)
- Only reindex modified documents
- Clean up deleted files automatically

**Memory Usage:**
- Batch processing prevents memory overflow
- Configurable batch sizes in config.py
- Default: 100 docs per batch, 10 embeddings per subbatch

## API Integration

The FastAPI backend (accessed via `run_api.py`) provides:
- Query endpoints for hybrid search
- Health check for retrieval system status
- Entity extraction endpoints
- Result fusion and ranking

**Expected API Structure** (in `streamlit-rag/api/`):
- `main.py` - FastAPI app instance
- `routes/` - API endpoint definitions
- `models/` - Pydantic request/response models
- `core/` - Core business logic

## Additional Resources

- **Database Schema**: See `README.md` lines 1-183 for complete SQL schema
- **Configuration Examples**: `.env.example` files (if present)
- **Supabase Docs**: https://supabase.com/docs/guides/database/extensions/pgvector
- **LlamaIndex Docs**: https://docs.llamaindex.ai/
- **Gemini API Docs**: https://ai.google.dev/docs
