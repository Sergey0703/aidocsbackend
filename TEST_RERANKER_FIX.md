# Testing the Reranker Fix

## Quick Test

Run these commands to verify the fix works:

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

# Test aggregation query
cd rag_client
python scripts/quick_search.py "how many cars we have"
```

## Expected Results

### Before Fix
```
Query: "how many cars we have"
Retrieved: 10 documents
Reranked: 0 documents (all filtered out by min_score threshold)
Answer: "I don't have enough information..."
```

### After Fix
```
Query: "how many cars we have"
Retrieved: 10 documents
Reranked: 10 documents (scored 3.0-7.0, all kept, sorted by score)
Answer: "Based on the documents, I see X vehicles: [list]"
```

## What Changed in Logs

### Before (OLD - filtering behavior)
```
[*] Reranking 10 results for query: 'how many cars we have'
   [-] Filtered (4.0/10): vehicle_registration_1.pdf
   [-] Filtered (3.5/10): vehicle_registration_2.pdf
   [-] Filtered (4.5/10): vehicle_registration_3.pdf
...
[+] Reranking complete: 10 -> 0 results
    Filtered out 10 irrelevant results
```

### After (NEW - ranking behavior)
```
[*] Reranking 10 results for query: 'how many cars we have'
   Scored (4.0/10): vehicle_registration_1.pdf
   Scored (3.5/10): vehicle_registration_2.pdf
   Scored (4.5/10): vehicle_registration_3.pdf
...
[+] Reranking complete: 10 -> 10 results
    Selected top 10 by relevance score (NO filtering by min_score)
```

## Additional Test Cases

### Test 1: Aggregation Query
```bash
python scripts/quick_search.py "tell me about all vehicles"
```
**Expected**: Should return information about multiple vehicles

### Test 2: Specific Entity Query
```bash
python scripts/quick_search.py "John Nolan"
```
**Expected**: Should return top-ranked documents about John Nolan

### Test 3: Count Query
```bash
python scripts/quick_search.py "how many documents about 231-D-54321"
```
**Expected**: Should count documents for that VRN

## Verification Checklist

- [ ] Aggregation queries return results (not "No information")
- [ ] Log shows "Scored (X/10)" instead of "Filtered (X/10)"
- [ ] Log shows "NO filtering by min_score"
- [ ] All retrieved documents are passed to answer generation
- [ ] LLM can perform counting and aggregation
- [ ] Results are sorted by relevance score

## Troubleshooting

### Issue: Still getting "No information" for aggregation queries

**Check**:
1. Did you restart the API server after making changes?
2. Is the reranker being used? Check logs for "[*] Reranking X results"
3. Are documents being retrieved? Check "Retrieved: X documents" in logs

### Issue: Too many low-quality results

**Solution**: Adjust `top_k` parameter in reranker call, not `min_score`

```python
# In your query engine
reranked_results = await reranker.rerank_results(
    query=query,
    results=retrieved_results,
    top_k=5  # Select top 5 after ranking (instead of filtering by score)
)
```

## Performance Notes

- Reranking time is the same (still evaluates all results)
- Answer generation may be slower (LLM sees more context)
- Quality improves for aggregation queries
- Precision improves for entity queries (better ranking)

## Next Steps

If tests pass:
1. Monitor production queries for aggregation improvements
2. Adjust `top_k` based on answer quality vs speed tradeoff
3. Consider caching reranking scores for repeated queries

If tests fail:
1. Check that changes were applied to `llm_reranker.py`
2. Verify no other code is filtering results after reranking
3. Check API server is using updated code (restart if needed)
