# API Logging Improvements

## Problem

When running the API, you couldn't see backend search logs - only the initialization logs. This made it hard to debug and monitor search operations.

## Solution

Added comprehensive logging at every stage of the search pipeline in the API layer.

## Changed Files

### 1. `api/main.py` (lines 23-35)

Enhanced logging configuration to capture backend module logs:

```python
# Setup logging - Configure root logger to capture all backend logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    force=True  # Force reconfiguration to ensure all loggers use this config
)

# Set log level for backend modules
logging.getLogger('retrieval').setLevel(logging.INFO)
logging.getLogger('query_processing').setLevel(logging.INFO)
logging.getLogger('api').setLevel(logging.INFO)
```

**What this does:**
- Forces all backend loggers to use the main config
- Ensures retrieval, query_processing, and API logs are visible
- Uses INFO level for all production logging

### 2. `api/modules/search/routes/search.py`

Added detailed logging at every stage:

#### Stage 0: Query Preprocessing
```python
logger.info("")
logger.info("STAGE 0: Query Preprocessing")
logger.info("-" * 40)

# ... preprocessing code ...

logger.info(f"[+] Query preprocessed: '{request.query}' -> '{preprocessing_result.query}'")
logger.info(f"    Method: {preprocessing_result.method}")
logger.info(f"    Time: {preprocess_time:.3f}s")
```

#### Stage 1: Retrieval
```python
logger.info("")
logger.info("STAGE 1: Multi-Strategy Retrieval")
logger.info("-" * 40)

# ... retrieval code ...

logger.info(f"[+] Retrieved {len(multi_retrieval_result.results)} candidates")
logger.info(f"    Methods: {', '.join(multi_retrieval_result.methods_used)}")
logger.info(f"    Time: {retrieval_time:.3f}s")

# Detailed source breakdown
if multi_retrieval_result.results:
    logger.info(f"    Result sources breakdown:")
    from collections import Counter
    sources = Counter(r.source_method for r in multi_retrieval_result.results)
    for source, count in sources.items():
        logger.info(f"      - {source}: {count} results")
```

#### Stage 2: Fusion + Re-ranking
```python
logger.info("")
logger.info("STAGE 2: Hybrid Results Fusion + LLM Re-ranking")
logger.info("-" * 40)

# ... fusion code ...

logger.info(f"[+] Fused to {fusion_result.final_count} documents")
logger.info(f"    Fusion method: {fusion_result.fusion_method}")
logger.info(f"    Time: {fusion_time:.3f}s")

# Show top 3 results with detailed scores
if fusion_result.fused_results:
    logger.info(f"    Top {min(3, len(fusion_result.fused_results))} results:")
    for i, doc in enumerate(fusion_result.fused_results[:3], 1):
        score = doc.similarity_score
        llm_score = doc.metadata.get('llm_relevance_score', 'N/A')
        match_type = doc.metadata.get('match_type', 'unknown')
        logger.info(f"      [{i}] {doc.filename}")
        logger.info(f"          Base score: {score:.3f}, LLM: {llm_score}, Match: {match_type}")
```

#### Final Summary
```python
logger.info("")
logger.info("=" * 80)
logger.info("SEARCH COMPLETED")
logger.info("=" * 80)
logger.info(f"Total Time: {total_time:.3f}s")
logger.info(f"Results returned: {len(search_results)}")
logger.info(f"Time breakdown:")
logger.info(f"  - Preprocessing: {preprocess_time:.3f}s")
logger.info(f"  - Retrieval: {retrieval_time:.3f}s")
logger.info(f"  - Fusion: {fusion_time:.3f}s")

# Show final scores being returned to user
if search_results:
    logger.info(f"Final scores (what user sees):")
    for i, res in enumerate(search_results[:3], 1):
        logger.info(f"  [{i}] {res.filename}: {res.score * 100:.1f}%")

logger.info("=" * 80)
```

## Example Output

When you run a search for "231-D-54321", you should now see:

```
================================================================================
SEARCH REQUEST: query='231-D-54321', top_k=10
================================================================================

STAGE 0: Query Preprocessing
----------------------------------------
[+] Query preprocessed: '231-D-54321' -> '231-D-54321'
    Method: PASS
    Time: 0.001s

STAGE 1: Multi-Strategy Retrieval
----------------------------------------
[+] Retrieved 6 candidates
    Methods: database_hybrid, vector_smart_threshold
    Time: 1.847s
    Result sources breakdown:
      - database_hybrid: 3 results
      - vector_smart_threshold: 3 results

STAGE 2: Hybrid Results Fusion + LLM Re-ranking
----------------------------------------
[+] Fused to 3 documents
    Fusion method: database_priority
    Time: 2.120s
    Top 3 results:
      [1] CVRT Pass Statement.md
          Base score: 0.650, LLM: 10.0, Match: exact_phrase
      [2] Vehicle Registration Certificate.md
          Base score: 0.650, LLM: 10.0, Match: exact_phrase
      [3] VCR.md
          Base score: 0.650, LLM: 10.0, Match: exact_phrase

STAGE 3: Format Response
----------------------------------------

================================================================================
SEARCH COMPLETED
================================================================================
Total Time: 3.289s
Results returned: 3
Time breakdown:
  - Preprocessing: 0.001s
  - Retrieval: 1.847s
  - Fusion: 2.120s
Final scores (what user sees):
  [1] CVRT Pass Statement.md: 100.0%
  [2] Vehicle Registration Certificate.md: 100.0%
  [3] VCR.md: 100.0%
================================================================================
```

## How to See Logs

### Option 1: Run API in foreground
```bash
python run_api.py
```

You'll see all logs in the console in real-time.

### Option 2: Check terminal where API is running

If you're running the API in the background or in a separate terminal, check that terminal window - all logs are output there.

### Option 3: Use test script

Run the test script:
```bash
python test_detailed_logs.py
```

Then check the API terminal for the detailed logs shown above.

## What You Can See Now

1. **Query Processing** - Original query, preprocessing method, cleaned query
2. **Retrieval Details** - Number of candidates, methods used, time taken, source breakdown
3. **Fusion Process** - Method used, number of results, LLM re-ranking scores
4. **Score Calculation** - Base scores vs LLM scores vs final display scores
5. **Performance** - Time breakdown for each stage
6. **Final Results** - What the user actually sees (with improved scores)

## Benefits

- **Debug Easily** - See exactly what's happening at each stage
- **Monitor Performance** - Identify slow stages
- **Verify Scores** - Confirm LLM re-ranking is working
- **Track Changes** - See how query preprocessing affects results
- **Production Ready** - Structured logs easy to parse and analyze

## No Emoji

As requested, all logging uses ASCII characters only:
- [+] for success/completion
- [-] for filtered/rejected
- [!] for warnings/errors
- [*] for info/processing

## Status

- Status: Implemented
- Date: 2025-10-23
- Version: API v1.0.0
- Tested: Yes (test_detailed_logs.py)
