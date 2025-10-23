# Score Display Improvement

## Problem

When users searched for documents (e.g., VRN "231-D-54321"), the search results showed misleading relevance scores:

**Example:**
- Query: "231-D-54321"
- Result: CVRT document containing that exact VRN
- Score shown to user: **65.8%** (looks like poor match!)
- Actual relevance: **Perfect match** (document contains exact VRN)

**Root cause:** The API was displaying the base `similarity_score` (0.658) which is just a fixed database result score, not reflecting actual document relevance.

## Solution

The API now intelligently selects the best score to display:

1. **Prioritize LLM relevance score** - If available, use the Gemini-evaluated semantic relevance score (0-10 scale, converted to 0-1)
2. **Boost exact matches** - For documents with `exact_match` type, show 0.95 (95%)
3. **Boost strong matches** - For `strong_match` type, show 0.85 (85%)
4. **Fallback to similarity score** - If no better score available, use base score

## Implementation

### File: `api/modules/search/routes/search.py`

**Lines 158-176:**
```python
# IMPROVED SCORE CALCULATION:
# Prioritize LLM relevance score (0-10 scale) over base similarity_score
# Convert to 0-1 scale for consistency
display_score = result.similarity_score  # Default fallback

if 'llm_relevance_score' in result.metadata:
    # LLM score is 0-10, convert to 0-1
    llm_score = result.metadata['llm_relevance_score']
    display_score = llm_score / 10.0
    logger.debug(f"[*] Using LLM score for {result.filename}: {llm_score}/10 = {display_score:.3f}")
elif result.metadata.get("match_type") == "exact_match":
    # Exact matches should show high confidence
    display_score = 0.95
elif result.metadata.get("match_type") == "strong_match":
    # Strong matches show high confidence
    display_score = 0.85

# Ensure score is in valid range
display_score = max(0.0, min(1.0, display_score))
```

**How it works:**
- Checks if LLM has evaluated this result
- If yes: Uses LLM score (0-10) converted to 0-1 scale
- If no: Checks match_type for semantic boosts
- Ensures score is always valid (0.0-1.0 range)

## Results

### Test Case: VRN Search "231-D-54321"

**BEFORE (misleading):**
```
Result: CVRT Pass Statement.md
Score: 65.0% (base database score)
User perception: "This is only 65% relevant??"
```

**AFTER (accurate):**
```
Result: CVRT Pass Statement.md
LLM Score: 10.0/10
Display Score: 100.0%
User perception: "Perfect match!"
```

**Improvement:** +35 percentage points

### API Response Comparison

**OLD response:**
```json
{
  "file_name": "CVRT Pass Statement.md",
  "score": 0.658,
  "similarity_score": 0.658,
  "metadata": {
    "llm_relevance_score": 10.0,
    "llm_is_relevant": true,
    "match_type": "exact_phrase"
  }
}
```
User sees: 65.8%

**NEW response:**
```json
{
  "file_name": "CVRT Pass Statement.md",
  "score": 1.0,
  "similarity_score": 1.0,
  "metadata": {
    "llm_relevance_score": 10.0,
    "llm_is_relevant": true,
    "match_type": "exact_phrase"
  }
}
```
User sees: 100.0%

## Verification

Run test script to verify improvement:

```bash
python test_api_score_fix.py
```

**Expected output:**
```
API SCORE FIX TEST
================================================================================
Query: 231-D-54321
[+] Received 3 results

SCORE ANALYSIS:
[1] CVRT Pass Statement.md
    DISPLAY SCORE: 100.0%
    LLM score: 10.0/10
    [+] Correct! Display score matches LLM score

[+] SUCCESS: API is using LLM score (10.0/10 = 100.0%)
    Score display is accurate and user-friendly!
```

## Benefits

1. **User Trust** - Scores now accurately reflect document relevance
2. **No Confusion** - 100% for perfect matches is intuitive
3. **Better UX** - Users can confidently identify best results
4. **Consistent** - Scores align with LLM semantic evaluation
5. **No Breaking Changes** - Metadata still available for debugging

## Technical Notes

- LLM re-ranking must be enabled in config (`reranking_enabled=True`)
- LLM scores are added to `result.metadata` during fusion
- Conversion: LLM score (0-10) / 10.0 = Display score (0-1)
- Frontend multiplies by 100 to show percentage
- Fallback mechanism ensures backwards compatibility

## Related Files

1. `api/modules/search/routes/search.py` - Score calculation logic
2. `retrieval/llm_reranker.py` - LLM relevance evaluation
3. `retrieval/results_fusion.py` - Async fusion with re-ranking
4. `test_api_score_fix.py` - Verification test
5. `streamlit-rag/scripts/test_score_display.py` - Backend test

## Status

- Status: Implemented and tested
- Date: 2025-10-23
- Version: API v1.0.0
- No emoji used (per user request)
