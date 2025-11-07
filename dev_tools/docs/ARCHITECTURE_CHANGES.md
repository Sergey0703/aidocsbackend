# Architecture Changes: Hybrid Chunking Migration

Visual guide to understand what changes in the system.

---

## Current Architecture (SentenceSplitter)

```
┌─────────────────────────────────────────────────────────────────────┐
│ PART 1: Document Conversion (docling_processor/)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PDF/DOCX ──┐                                                       │
│             ├──► Docling ──► Markdown ──► OCR Enhancer ──┐          │
│  Images ────┘                                            │          │
│                                                          ▼          │
│                                            rag_indexer/data/markdown │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PART 2: Chunking & Vectors (chunking_vectors/)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Markdown Files                                                     │
│       │                                                             │
│       ▼                                                             │
│  MarkdownLoader ──► Documents (LlamaIndex)                          │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────┐                           │
│  │ SentenceSplitter                   │ ◄── CURRENT                │
│  ├─────────────────────────────────────┤                           │
│  │ • Fixed chunk size (512 chars)      │                           │
│  │ • Fixed overlap (128 chars)         │                           │
│  │ • No structure awareness            │                           │
│  │ • Splits at sentence boundaries     │                           │
│  └─────────────────────────────────────┘                           │
│       │                                                             │
│       ▼                                                             │
│  Text Nodes (chunks)                                                │
│       │                                                             │
│       ▼                                                             │
│  Embedding Processor ──► Gemini API ──► Embeddings (768D)          │
│       │                                                             │
│       ▼                                                             │
│  Database Manager ──► vecs.documents (PostgreSQL + pgvector)        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RETRIEVAL (client_rag/)                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Query ──► Vector Search ──┐                                        │
│                            ├──► Hybrid Fusion ──► Results           │
│  Query ──► Database Search ─┘                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## New Architecture (HybridChunker)

```
┌─────────────────────────────────────────────────────────────────────┐
│ PART 1: Document Conversion (docling_processor/)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PDF/DOCX ──┐                                                       │
│             ├──► Docling ──► Markdown ──► OCR Enhancer ──┐          │
│  Images ────┘                                            │          │
│                                                          ▼          │
│                                            rag_indexer/data/markdown │
│                                                                     │
│  ⚠️ NO CHANGES IN PART 1                                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PART 2: Chunking & Vectors (chunking_vectors/)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Markdown Files                                                     │
│       │                                                             │
│       ▼                                                             │
│  MarkdownLoader ──► Documents (LlamaIndex)                          │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────┐                           │
│  │ IF USE_HYBRID_CHUNKING=true         │ ◄── NEW FLAG              │
│  └─────────────────────────────────────┘                           │
│       │                                                             │
│       ├─── true ──► ┌──────────────────────────────────┐           │
│       │             │ HybridChunker (Docling)         │ ◄── NEW    │
│       │             ├──────────────────────────────────┤           │
│       │             │ • Token-aware sizing            │           │
│       │             │ • Structure preservation        │           │
│       │             │ • Tables stay intact            │           │
│       │             │ • Heading hierarchy             │           │
│       │             │ • Metadata: chunk_type,         │           │
│       │             │   doc_items, parent_heading     │           │
│       │             └──────────────────────────────────┘           │
│       │                      │                                     │
│       └─── false ─► ┌──────────────────────────────────┐           │
│                     │ SentenceSplitter (Legacy)       │ ◄── FALLBACK │
│                     ├──────────────────────────────────┤           │
│                     │ • Fixed chunk size (512 chars)  │           │
│                     │ • Fixed overlap (128 chars)     │           │
│                     └──────────────────────────────────┘           │
│                              │                                     │
│       ┌──────────────────────┴──────────────────────┐             │
│       ▼                                             ▼             │
│  Text Nodes (hybrid chunks)                  Text Nodes (legacy)  │
│       │                                             │             │
│       └──────────────────┬──────────────────────────┘             │
│                          ▼                                        │
│  Embedding Processor ──► Gemini API ──► Embeddings (768D)         │
│       │                                                            │
│       ▼                                                            │
│  Database Manager ──► vecs.documents (PostgreSQL + pgvector)       │
│                                                                    │
│  ⚠️ CHANGES: hybrid_chunker.py (NEW), config.py, chunk_helpers.py  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RETRIEVAL (client_rag/)                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Query ──► Vector Search ──┐                                        │
│                            ├──► Hybrid Fusion ──► Results           │
│  Query ──► Database Search ─┘                                       │
│                                                                     │
│  ⚠️ NO CODE CHANGES - Just richer metadata in chunks                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Comparison

### Current Flow (SentenceSplitter)

```
Markdown Document (5000 chars, 3 tables, 2 headings)
           │
           ▼
   SentenceSplitter
           │
           ├──► Chunk 1: 512 chars (heading + partial paragraph)
           ├──► Chunk 2: 512 chars (rest of paragraph + partial table)
           ├──► Chunk 3: 512 chars (rest of table)    ◄── TABLE SPLIT!
           ├──► Chunk 4: 512 chars (another paragraph)
           └──► Chunk 5: 384 chars (final content)
                      │
                      ▼
              Total: 5 chunks
              Metadata: file_name, registry_id
```

### New Flow (HybridChunker)

```
Markdown Document (5000 chars, 3 tables, 2 headings)
           │
           ▼
     HybridChunker
           │
           ├──► Chunk 1: 480 chars (heading + paragraph)
           │    metadata: {chunk_type: 'text', parent_heading: 'Chapter 1'}
           │
           ├──► Chunk 2: 820 chars (COMPLETE table)    ◄── TABLE INTACT!
           │    metadata: {chunk_type: 'table', doc_items: ['TABLE']}
           │
           ├──► Chunk 3: 650 chars (next heading + paragraph)
           │    metadata: {chunk_type: 'text', parent_heading: 'Chapter 2'}
           │
           └──► Chunk 4: 720 chars (another paragraph + list)
                metadata: {chunk_type: 'mixed', doc_items: ['TEXT', 'LIST']}
                      │
                      ▼
              Total: 4 chunks
              Metadata: file_name, registry_id, chunk_type, doc_items,
                        parent_heading, chunking_method
```

---

## Metadata Structure Comparison

### Current Metadata (SentenceSplitter)

```json
{
  "file_path": "/path/to/file.md",
  "file_name": "document.md",
  "file_type": "markdown",
  "file_size": 15420,
  "content_length": 512,
  "word_count": 89,
  "loader_timestamp": "2025-01-21T10:30:00",
  "registry_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### New Metadata (HybridChunker)

```json
{
  "file_path": "/path/to/file.md",
  "file_name": "document.md",
  "file_type": "markdown",
  "file_size": 15420,
  "content_length": 820,
  "word_count": 142,
  "loader_timestamp": "2025-01-21T10:30:00",
  "registry_id": "550e8400-e29b-41d4-a716-446655440000",

  "chunking_method": "hybrid_docling",      ◄── NEW
  "chunk_type": "table",                    ◄── NEW
  "doc_items": ["TABLE"],                   ◄── NEW
  "parent_heading": "Performance Metrics",  ◄── NEW
  "headings": ["Chapter 1", "Performance Metrics"]  ◄── NEW
}
```

---

## Code Changes Map

### Files to CREATE

```
rag_indexer/chunking_vectors/
└── hybrid_chunker.py                  ◄── NEW (380 lines)
    ├── HybridChunkerWrapper class
    ├── _initialize_tokenizer()
    ├── _initialize_chunker()
    ├── _markdown_to_docling_document()
    ├── _docling_chunk_to_llamaindex_node()
    └── chunk_documents()
```

### Files to UPDATE

```
rag_indexer/
├── .env                               ◄── ADD 6 lines
│   ├── USE_HYBRID_CHUNKING=true
│   ├── HYBRID_MAX_TOKENS=512
│   ├── HYBRID_MERGE_PEERS=true
│   ├── HYBRID_USE_CONTEXTUALIZE=false
│   ├── HYBRID_TOKENIZER=huggingface
│   └── HYBRID_TOKENIZER_MODEL=sentence-transformers/all-MiniLM-L6-v2
│
└── chunking_vectors/
    ├── config.py                      ◄── ADD ~20 lines
    │   ├── Add 6 config variables
    │   └── Add get_hybrid_chunking_settings() method
    │
    └── chunk_helpers.py               ◄── UPDATE ~50 lines
        └── Update create_and_filter_chunks_enhanced()
            ├── Add hybrid chunking path
            ├── Add SentenceSplitter fallback
            └── Preserve all existing filtering logic
```

### Files with NO CHANGES

```
client_rag/
├── retrieval/
│   ├── multi_retriever.py             ◄── NO CHANGES
│   └── results_fusion.py              ◄── NO CHANGES
├── query_processing/
│   ├── entity_extractor.py            ◄── NO CHANGES
│   └── query_rewriter.py              ◄── NO CHANGES
└── config/
    └── settings.py                    ◄── NO CHANGES
```

---

## Database Schema (No Changes)

```sql
-- vecs.documents table structure stays EXACTLY the same

CREATE TABLE vecs.documents (
    id TEXT PRIMARY KEY,               -- Same
    vec vector(768),                   -- Same (768D Gemini embeddings)
    metadata JSONB,                    -- Same (just richer content)
    FOREIGN KEY (metadata->>'registry_id')
        REFERENCES vecs.document_registry(id)
);

-- Sample metadata BEFORE (SentenceSplitter):
{
  "file_name": "doc.md",
  "registry_id": "uuid-here"
}

-- Sample metadata AFTER (HybridChunker):
{
  "file_name": "doc.md",
  "registry_id": "uuid-here",
  "chunk_type": "table",           ◄── NEW field
  "doc_items": ["TABLE"],          ◄── NEW field
  "parent_heading": "Chapter 1"    ◄── NEW field
}

-- ✅ Backward compatible (old fields still present)
-- ✅ Search works with both formats
```

---

## Dependency Tree

### Current Dependencies

```
rag_indexer/
├── python 3.9+
├── llama-index
├── llama-index-embeddings-google-genai
├── llama-index-vector-stores-supabase
└── transformers (for sentence splitting)
```

### New Dependencies

```
rag_indexer/
├── python 3.9+
├── llama-index
├── llama-index-embeddings-google-genai
├── llama-index-vector-stores-supabase
├── transformers (existing)
├── docling-core[chunking]          ◄── NEW
└── (tiktoken - optional for OpenAI tokenizer)
```

---

## Processing Pipeline Changes

### Step-by-Step: Document → Chunks → Vectors

```
┌────────────────────────────────────────────────────────────┐
│ STEP 1: Load Documents                                    │
├────────────────────────────────────────────────────────────┤
│ markdown_loader.py                                         │
│   • Scan markdown files                                    │
│   • Load content                                           │
│   • Enrich with registry_id                                │
│   • Create LlamaIndex Documents                            │
│                                                            │
│ ✅ NO CHANGES                                              │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 2: Chunk Documents                                   │
├────────────────────────────────────────────────────────────┤
│ chunk_helpers.py → create_and_filter_chunks_enhanced()     │
│                                                            │
│ IF USE_HYBRID_CHUNKING=true:                               │
│   ┌────────────────────────────────────┐                  │
│   │ hybrid_chunker.py (NEW)           │                  │
│   ├────────────────────────────────────┤                  │
│   │ 1. Convert MD → DoclingDocument   │                  │
│   │ 2. Run HybridChunker              │                  │
│   │ 3. Get structure-aware chunks     │                  │
│   │ 4. Convert to LlamaIndex nodes    │                  │
│   │ 5. Preserve metadata              │                  │
│   └────────────────────────────────────┘                  │
│ ELSE:                                                      │
│   ┌────────────────────────────────────┐                  │
│   │ SentenceSplitter (existing)       │                  │
│   ├────────────────────────────────────┤                  │
│   │ 1. Split at sentence boundaries   │                  │
│   │ 2. Fixed size (512 chars)         │                  │
│   │ 3. Fixed overlap (128 chars)      │                  │
│   └────────────────────────────────────┘                  │
│                                                            │
│ ⚠️ CHANGES: Add hybrid path + fallback                     │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 3: Filter Chunks                                     │
├────────────────────────────────────────────────────────────┤
│ chunk_helpers.py                                           │
│   • Remove too short chunks                                │
│   • Remove null bytes                                      │
│   • Validate content                                       │
│                                                            │
│ ✅ NO CHANGES (same logic for both methods)                │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 4: Generate Embeddings                               │
├────────────────────────────────────────────────────────────┤
│ embedding_processor.py                                     │
│   • Batch processing                                       │
│   • Gemini API calls                                       │
│   • Rate limiting                                          │
│   • 768D embeddings                                        │
│                                                            │
│ ✅ NO CHANGES                                              │
└────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ STEP 5: Save to Database                                  │
├────────────────────────────────────────────────────────────┤
│ database_manager.py                                        │
│   • vecs.documents table                                   │
│   • id (TEXT), vec (vector), metadata (JSONB)             │
│   • Foreign key to document_registry                       │
│                                                            │
│ ✅ NO CHANGES (just richer metadata)                       │
└────────────────────────────────────────────────────────────┘
```

---

## Performance Comparison

### SentenceSplitter (Current)

```
┌──────────────────────────────────────┐
│ Processing 100 documents             │
├──────────────────────────────────────┤
│ • Load: 2s                           │
│ • Chunk (SentenceSplitter): 5s       │
│ • Embeddings: 30s                    │
│ • Database save: 3s                  │
├──────────────────────────────────────┤
│ TOTAL: ~40s                          │
│ Chunks created: ~450                 │
│ Avg chunk size: 487 chars            │
└──────────────────────────────────────┘
```

### HybridChunker (Expected)

```
┌──────────────────────────────────────┐
│ Processing 100 documents             │
├──────────────────────────────────────┤
│ • Load: 2s                           │
│ • Chunk (HybridChunker): 9s (+4s)    │ ◄── Slower
│ • Embeddings: 28s (-2s)              │ ◄── Fewer chunks
│ • Database save: 3s                  │
├──────────────────────────────────────┤
│ TOTAL: ~42s (+5% slower)             │
│ Chunks created: ~420 (-7%)           │ ◄── Larger chunks
│ Avg chunk size: 523 chars            │
└──────────────────────────────────────┘
```

**Conclusion**: ~5-10% slower, but better quality chunks

---

## Migration Decision Points

### Should I migrate if...

```
┌─────────────────────────────────────────────────────┐
│ My documents have many tables?                      │
│ ✅ YES - Tables won't be split anymore              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ My documents are mostly plain text?                 │
│ ⚠️ MAYBE - Still get better metadata, minor benefit │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ I need to know document structure (headings)?       │
│ ✅ YES - HybridChunker preserves hierarchy          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Performance is critical (real-time indexing)?       │
│ ⚠️ MAYBE - HybridChunker is 1.5-2x slower          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ I want better search quality?                       │
│ ✅ YES - Structure-aware chunks improve context     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ I'm worried about breaking things?                  │
│ ✅ SAFE - Backward compatible, easy rollback        │
└─────────────────────────────────────────────────────┘
```

---

**Last Updated**: 2025-01-21
**Version**: 1.0
