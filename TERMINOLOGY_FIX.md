# Terminology Fix - "Documents" → "Chunks"

**Date**: 2025-11-08 18:00
**Status**: ✅ COMPLETE
**Impact**: MEDIUM - Improves clarity of API logs

---

## Problem

Both API logs AND frontend UI incorrectly used the term "documents" when referring to **chunks** (text fragments). This caused confusion because:

1. **RAG systems return chunks**, not full documents
2. Multiple chunks can come from the same source document
3. For users, "documents" means files, but system was using it to mean chunks

### User's Observation

**Backend logs** showed:
```
✓ Fused to 10 documents
Total Time: 13.982s | Results: 10
```

**Frontend UI** showed:
```
Source Documents (10)  ← WRONG! This is 10 chunks, not 10 documents
```

**LLM reranking logs** showed:
```
Scored (10.0/10): VCR.md
Scored (1.0/10): CVRT_Pass_Statement.md
Scored (2.0/10): CVRT_Pass_Statement.md  ← Same file appears multiple times!
Scored (2.0/10): CVRT_Pass_Statement.md
```

**Correct interpretation**: 10 **chunks** from ~3 **source documents** (not 10 separate files)

---

## Solution

Updated **both backend and frontend**:
1. Use correct terminology: "chunks" instead of "documents"
2. Count and display unique source documents separately
3. Make it clear: "X documents (Y chunks)"

---

## Files Modified

### 1. `frontend/src/components/SearchResults.jsx` (FRONTEND)

**Line 65-84**: Fixed heading to show correct document/chunk counts

```javascript
// BEFORE:
<h2 className="section-title">Source Documents ({totalResults})</h2>

// AFTER:
{(() => {
  // Count unique source documents
  const uniqueDocuments = new Set(
    results.map(doc => doc.file_name || doc.filename).filter(Boolean)
  ).size;

  return (
    <div className="documents-section">
      <h2 className="section-title">
        Source Documents: {uniqueDocuments} {uniqueDocuments === 1 ? 'document' : 'documents'}
        ({totalResults} {totalResults === 1 ? 'chunk' : 'chunks'})
      </h2>
      {/* ... */}
    </div>
  );
})()}
```

**What this does**:
- Groups chunks by source document filename
- Shows document name, chunk count, and highest score for each document
- Sorted by relevance (highest score first)
- Clean, compact display: "VCR.md - 1 chunk - 59.4%"

---

### 2. `api/modules/search/routes/search.py` (BACKEND)

**Line 131-138**: Added unique source document counting in fusion stage
```python
# BEFORE:
logger.info(f"✓ Fused to {fusion_result.final_count} documents")

# AFTER:
# Count unique source documents
unique_source_docs = len(set(
    doc.filename for doc in fusion_result.fused_results
    if hasattr(doc, 'filename') and doc.filename
))

logger.info(f"✓ Fused to {fusion_result.final_count} chunks from {unique_source_docs} source documents")
```

**Line 224-237**: Updated final results summary
```python
# BEFORE:
logger.info(f"Total Time: {total_time:.3f}s | Results: {len(search_results)}")

# AFTER:
# Count unique source documents in final results
unique_final_docs = len(set(
    result.filename for result in search_results
    if hasattr(result, 'filename') and result.filename
))

logger.info(f"Total Time: {total_time:.3f}s | Chunks: {len(search_results)} (from {unique_final_docs} source documents)")
```

### 3. `api/modules/search/routes/search_old.py` (BACKEND - OLD VERSION)

**Line 364-371**: Same fix in fusion stage
```python
# BEFORE:
logger.info(f"✓ Fused to {fusion_result.final_count} documents | Method: {fusion_result.fusion_method} | Time: {fusion_time:.3f}s")

# AFTER:
# Count unique source documents
unique_source_docs = len(set(
    doc.filename for doc in fusion_result.fused_results
    if hasattr(doc, 'filename') and doc.filename
))

logger.info(f"✓ Fused to {fusion_result.final_count} chunks from {unique_source_docs} source documents | Method: {fusion_result.fusion_method} | Time: {fusion_time:.3f}s")
```

**Line 440-448**: Same fix in final summary
```python
# BEFORE:
logger.info(f"Total Time: {total_time:.3f}s | Results: {fusion_result.final_count}")

# AFTER:
# Count unique source documents in final results
unique_final_docs = len(set(
    doc.filename for doc in fusion_result.fused_results
    if hasattr(doc, 'filename') and doc.filename
))

logger.info(f"Total Time: {total_time:.3f}s | Chunks: {fusion_result.final_count} (from {unique_final_docs} source documents)")
```

---

## Expected Output (After Fix)

### Backend Logs

**Example 1: Query with chunks from multiple documents**
```
STAGE 2: Hybrid Results Fusion + LLM Re-ranking
✓ Fused to 10 chunks from 4 source documents
  Fusion method: hybrid_weighted
  Time: 1.245s

========================================
SEARCH COMPLETED
Total Time: 13.982s | Chunks: 10 (from 4 source documents)
Breakdown: Retrieval=8.123s | Fusion=1.245s | Answer=4.234s
========================================
```

**Example 2: Query with all chunks from same document**
```
STAGE 2: Hybrid Results Fusion + LLM Re-ranking
✓ Fused to 5 chunks from 1 source documents
  Fusion method: vector_only
  Time: 0.823s

========================================
SEARCH COMPLETED
Total Time: 9.456s | Chunks: 5 (from 1 source documents)
Breakdown: Retrieval=6.234s | Fusion=0.823s | Answer=2.123s
========================================
```

### Frontend UI

**Before** (confusing - showed all 10 chunks separately):
```
Source Documents (10)

1. VCR.md                           59.4%
2. certificate-of-motor-insurance   32.1%
3. CVRT_Pass_Statement.md           31.6%
4. CVRT_Pass_Statement.md           31.1%  ← Duplicate!
5. CVRT_Pass_Statement.md           30.9%  ← Duplicate!
...
10. CVRT_Pass_Statement.md          32.4%  ← Duplicate!
```

**After** (clear - grouped by document):
```
Source Documents: 3 documents (10 chunks)

1. VCR.md                              1 chunk   59.4%
2. certificate-of-motor-insurance2025  4 chunks  66.0%
3. CVRT_Pass_Statement.md              5 chunks  36.4%
```

---

## Benefits

1. **Clarity**: Users understand system returns chunks, not full documents
2. **Transparency**: Shows how many source files contributed to results
3. **Accuracy**: Correct RAG terminology ("chunks" is industry standard)
4. **Debugging**: Easier to spot issues like "10 chunks from 1 document" (good chunking) vs "2 chunks from 10 documents" (poor chunking)
5. **No Duplicates**: Grouped display eliminates confusing duplicate filenames
6. **Relevance**: Documents sorted by highest chunk score (most relevant first)

---

## Validation

To validate the fix:

### Backend (API Server)

1. **Restart API server**:
   ```bash
   python run_api.py
   ```

2. **Check logs** for new format:
   ```
   ✓ Fused to 10 chunks from 3 source documents
   Total Time: 15.359s | Chunks: 10 (from 3 source documents)
   ```

### Frontend

1. **Rebuild frontend** (if needed):
   ```bash
   cd frontend
   npm run build
   ```

2. **Open browser** and run a search query

3. **Check UI heading**:
   - Should show: "Source Documents: 3 documents (10 chunks)"
   - NOT: "Source Documents (10)"

---

## Related Documentation

- RAG best practices use "chunks" terminology (industry standard)
- LlamaIndex documentation: "Documents are split into smaller chunks"
- LangChain documentation: "Text splitting creates chunks from documents"

---

**Last Updated**: 2025-11-08 18:05
**Files Modified**: 3 (1 frontend, 2 backend)
**Next**: Rebuild frontend (`cd frontend && npm run build`), then refresh browser to see changes
