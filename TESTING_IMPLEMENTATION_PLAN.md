# RAG Testing Implementation Plan

## Summary

Документация по тестированию RAG системы создана на основе **Ragas framework** (gold standard для RAG testing) и лучших практик production RAG систем.

## Что уже сделано ✅

1. **Comprehensive Testing Guide** - [dev_tools/RAG_TESTING_GUIDE.md](dev_tools/RAG_TESTING_GUIDE.md)
   - 4-dimensional testing methodology (Retrieval, Faithfulness, Relevance, Context)
   - Test categories and patterns
   - Metrics and benchmarks
   - Execution workflow

2. **Ground Truth Dataset** - [dev_tools/datasets/ground_truth/vehicle_queries.json](dev_tools/datasets/ground_truth/vehicle_queries.json)
   - 15 manually verified test cases
   - Covers all query types (VRN, aggregation, entity, semantic, negative)
   - Expected results and metrics for each test

3. **Directory Structure** - Created test framework directories:
   ```
   dev_tools/
   ├── datasets/ground_truth/
   ├── datasets/synthetic/
   ├── benchmarks/
   └── tests/rag_evaluation/
   ```

4. **CLAUDE.md Integration** - Added testing section to project documentation
   - Testing methodology overview
   - Key metrics and benchmarks
   - Running instructions

## Next Steps (Implementation)

### Phase 1: Database Snapshot Script (Priority: HIGH)

**Goal:** Understand what documents exist in the database

**Script to create:** `dev_tools/scripts/diagnostics/snapshot_database.py`

**What it does:**
```python
# Connect to database
# Query vecs.documents and vecs.document_registry
# Extract:
#   - List of all document filenames
#   - List of all VRNs mentioned
#   - Document count by type
#   - Available entities (owners, makes, models)
# Save to: dev_tools/datasets/ground_truth/database_snapshot.json
```

**Why needed:**
- Tests must know what data exists
- Validate ground truth queries are realistic
- Track data changes over time

**Example output:**
```json
{
  "snapshot_date": "2025-11-08",
  "total_documents": 6,
  "total_chunks": 150,
  "documents": [
    "CVRT_Pass_Statement.md",
    "certificate-of-motor-insurance2025.md",
    "VCR.md",
    "VCR2.md",
    "VCR_-_Copy.md",
    "Vehicle_Registration_Certificate.md"
  ],
  "vrns": ["231-D-54321", "141-D-98765", "231-D-55555", "231-D-54329"],
  "entities": {
    "owners": ["Murphy Builders Ltd", "Dublin Transport Logistics Ltd"],
    "makes": ["Ford", "Volvo"],
    "models": ["Transit Connect", "FH460"]
  }
}
```

### Phase 2: Smoke Test (Priority: HIGH)

**Goal:** Quick sanity check (< 1 minute)

**Script to create:** `dev_tools/tests/rag_evaluation/smoke_test.py`

**What it does:**
```python
# Load 5 critical test cases from vehicle_queries.json
# For each test:
#   1. Send query to API
#   2. Verify response received
#   3. Check if expected keywords in answer
#   4. Log PASS/FAIL
# Print summary
```

**Test cases for smoke test:**
- 1 exact VRN lookup (vrn_001)
- 1 aggregation query (agg_001)
- 1 entity search (entity_001)
- 1 semantic query (semantic_001)
- 1 negative test (neg_001)

**Expected output:**
```
=======================================
SMOKE TEST (Quick Sanity Check)
=======================================

[PASS] vrn_001: "231-D-54321" (1.2s)
  ✓ Expected keywords found: ['231-D-54321', 'Volvo', 'FH460']

[PASS] agg_001: "how many cars we have?" (5.3s)
  ✓ Expected keywords found: ['four', '4']

[FAIL] neg_001: "What is the biggest river in USA?" (2.1s)
  ✗ Should reject but gave confident answer

=======================================
RESULT: 4/5 PASSED (80%)
=======================================
```

### Phase 3: Retrieval Quality Test (Priority: MEDIUM)

**Goal:** Measure retrieval accuracy

**Script to create:** `dev_tools/tests/rag_evaluation/test_retrieval.py`

**What it does:**
```python
# For each test case in ground_truth:
#   1. Call retriever directly (bypass answer generation)
#   2. Check if relevant_documents are in top K
#   3. Calculate metrics:
#      - Precision@K: % of top K that are relevant
#      - Recall@K: % of relevant docs in top K
#      - MRR (Mean Reciprocal Rank)
# Save metrics to: dev_tools/benchmarks/retrieval_metrics.json
```

**Metrics:**
- Precision@5
- Recall@10
- MRR (Mean Reciprocal Rank)
- Success rate by query type

### Phase 4: Faithfulness Test (Priority: MEDIUM)

**Goal:** Detect hallucinations

**Script to create:** `dev_tools/tests/rag_evaluation/test_faithfulness.py`

**Uses:** Ragas Faithfulness metric

**What it does:**
```python
from ragas.metrics import Faithfulness

# For each test case:
#   1. Get answer from RAG pipeline
#   2. Get retrieved contexts
#   3. Calculate Faithfulness score
#   4. Check if > min_faithfulness threshold
# Report cases with low faithfulness (potential hallucinations)
```

**Key insight:**
- Faithfulness checks if answer is **grounded in retrieved context**
- Does NOT check if answer is correct (that's Answer Correctness)
- Low faithfulness = hallucination risk

### Phase 5: End-to-End Test Suite (Priority: MEDIUM)

**Goal:** Complete quality assessment

**Script to create:** `dev_tools/tests/rag_evaluation/run_full_suite.py`

**What it does:**
```python
# Run ALL tests from ground_truth dataset
# For each test:
#   1. Query API
#   2. Measure latency
#   3. Check expected_answer_contains
#   4. Calculate all metrics (if Ragas installed)
# Generate comprehensive report
```

**Output:**
```
=======================================
FULL TEST SUITE RESULTS
=======================================

Total queries: 15
Passed: 13/15 (86.7%)
Failed: 2/15 (13.3%)

By Query Type:
  exact_vrn_lookup: 2/2 (100%)
  aggregation: 2/2 (100%)
  entity_search: 1/1 (100%)
  semantic_search: 2/2 (100%)
  document_type_search: 2/2 (100%)
  negative: 2/3 (66.7%)  ⚠️
  edge_case: 1/1 (100%)

Metrics:
  Avg latency: 4.2s
  Retrieval precision@5: 0.82
  Answer faithfulness: 0.87
  Answer relevancy: 0.91

⚠️ ALERTS:
  - Negative test "neg_002" failed (system answered Tesla query)
  - Latency for "complex_001" exceeded 10s threshold
```

### Phase 6: Baseline Capture (Priority: LOW)

**Goal:** Track metrics over time

**Script to create:** `dev_tools/tests/rag_evaluation/capture_baseline.py`

**What it does:**
```python
# Run full test suite
# Extract key metrics
# Save to: dev_tools/benchmarks/baseline_{date}.json
# Compare with previous baseline (if exists)
# Alert if metrics dropped > 5%
```

### Phase 7: Pre-Deployment Validation (Priority: LOW)

**Goal:** Gate for production deployments

**Script to create:** `dev_tools/tests/rag_evaluation/pre_deployment.py`

**What it does:**
```python
# Run critical path tests (must all pass)
# Check for regressions vs baseline
# Verify performance benchmarks
# PASS/FAIL decision for deployment
```

## Implementation Priority

### Week 1 (Now)
1. ✅ Read RAG_TESTING_GUIDE.md
2. ✅ Review vehicle_queries.json ground truth
3. 🔧 Implement snapshot_database.py
4. 🔧 Implement smoke_test.py
5. 📝 Update ground truth based on database snapshot

### Week 2
6. 🔧 Implement test_retrieval.py
7. 🧪 Run retrieval tests on current system
8. 📊 Establish baseline metrics

### Week 3
9. 🔧 Implement test_faithfulness.py (if Ragas available)
10. 🔧 Implement run_full_suite.py
11. 📈 Generate first comprehensive report

### Week 4
12. 🔧 Set up CI/CD integration
13. 📊 Create metrics dashboard
14. 🔔 Configure alerts

## Dependencies

**Python Packages (Optional):**
```bash
pip install ragas  # For advanced metrics (Faithfulness, Relevance)
pip install datasets  # For test data management
```

**Note:** Basic tests can run WITHOUT Ragas (using keyword matching and basic checks)

## Success Criteria

### Minimum Viable Testing (MVP)
- ✅ Smoke test runs in < 1 minute
- ✅ Covers 5 critical query types
- ✅ Alerts on failures

### Complete Testing Suite
- ✅ All 15 ground truth tests passing
- ✅ Metrics tracked over time
- ✅ Regression detection working
- ✅ Automated in CI/CD

### Production Grade
- ✅ Real-time monitoring
- ✅ Synthetic test generation
- ✅ A/B testing support
- ✅ User feedback integration

## Files Created

1. ✅ `dev_tools/RAG_TESTING_GUIDE.md` - Complete testing methodology
2. ✅ `dev_tools/datasets/ground_truth/vehicle_queries.json` - 15 test cases
3. ✅ `CLAUDE.md` (updated) - Testing section added
4. ✅ `TESTING_IMPLEMENTATION_PLAN.md` (this file)

## Next Action

**Immediate next step:**

```bash
# Create database snapshot script
# This is the foundation for all other tests
cd dev_tools/scripts/diagnostics
# Create snapshot_database.py (see Phase 1 above)
```

После создания snapshot скрипта - можно валидировать ground truth и начать имплементацию smoke test.

## Notes

- Тестирование основано на Ragas framework - gold standard для RAG
- Можно начать с простых тестов (keyword matching) без Ragas
- Постепенно добавлять метрики (Faithfulness, Relevancy)
- Главное - **регулярно запускать** тесты при изменениях
- Ground truth должен **эволюционировать** вместе с системой
