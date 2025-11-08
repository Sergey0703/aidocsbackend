# RAG System Testing Guide

## Overview

This guide provides comprehensive testing methodology for the Vehicle Documentation RAG system based on **Ragas** best practices and production testing standards.

## Testing Philosophy

Based on Ragas framework, RAG testing has **4 key dimensions**:

1. **Retrieval Quality** - Are the right documents retrieved?
2. **Answer Faithfulness** - Is the answer grounded in retrieved context?
3. **Answer Relevance** - Does the answer address the question?
4. **Context Precision** - Are relevant contexts ranked higher?

## Test Suite Structure

```
dev_tools/
├── tests/
│   ├── rag_evaluation/           # New: Ragas-based evaluation
│   │   ├── test_retrieval.py     # Retrieval metrics
│   │   ├── test_faithfulness.py  # Answer faithfulness
│   │   ├── test_relevance.py     # Answer relevance
│   │   └── test_e2e.py           # End-to-end RAG pipeline
│   ├── test_vector_search.py     # Existing: Vector search quality
│   └── test_answer_generation.py # Existing: Answer generation
├── datasets/
│   ├── ground_truth/             # Human-verified Q&A pairs
│   │   ├── vehicle_queries.json  # Vehicle-related queries
│   │   ├── aggregation_queries.json  # "how many" queries
│   │   └── negative_queries.json # Out-of-domain queries
│   └── synthetic/                # AI-generated test data
│       └── generated_testset.json
└── benchmarks/
    └── baseline_results.json     # Baseline metrics to track regression
```

## Testing Methodology

### Phase 1: Database Snapshot (Prerequisite)

Before running tests, create a snapshot of available documents:

```bash
python dev_tools/scripts/diagnostics/snapshot_database.py
```

**Output:**
- `datasets/ground_truth/database_snapshot.json`
  - List of all documents (filenames, VRNs, document types)
  - Available entities (vehicles, drivers)
  - Document statistics (count by type)

**Why:** Tests should know what data exists to create realistic queries.

### Phase 2: Ground Truth Preparation

#### 2.1 Manual Ground Truth (High Quality)

Create `datasets/ground_truth/vehicle_queries.json`:

```json
{
  "test_cases": [
    {
      "query": "What is the registration number for the Ford Transit?",
      "expected_vrn": "231-D-54321",
      "expected_answer_contains": ["231-D-54321", "Ford", "Transit"],
      "relevant_documents": ["Vehicle_Registration_Certificate.md"],
      "query_type": "entity_extraction",
      "difficulty": "easy"
    },
    {
      "query": "How many vehicles do we have registered?",
      "expected_count": 4,
      "expected_answer_contains": ["four", "4", "vehicles"],
      "query_type": "aggregation",
      "difficulty": "medium"
    },
    {
      "query": "Tell me about insurance for 231-D-54321",
      "expected_answer_contains": ["insurance", "231-D-54321", "valid"],
      "relevant_documents": ["certificate-of-motor-insurance2025.md"],
      "query_type": "document_retrieval",
      "difficulty": "easy"
    }
  ]
}
```

#### 2.2 Synthetic Test Generation (Ragas-based)

```python
# dev_tools/tests/rag_evaluation/generate_synthetic_tests.py
from ragas.testset.generator import TestsetGenerator
from ragas.testset.evolutions import simple, reasoning, multi_context

# Generate diverse test questions from your documents
generator = TestsetGenerator.with_openai()

distributions = {
    simple: 0.5,          # Simple fact retrieval
    reasoning: 0.3,       # Multi-step reasoning
    multi_context: 0.2    # Cross-document queries
}

testset = generator.generate_with_llamaindex_docs(
    documents=your_documents,
    test_size=50,
    distributions=distributions
)
```

**Why Synthetic Tests:**
- Cover edge cases humans might miss
- Test multi-document reasoning
- Ensure diverse query patterns

### Phase 3: Test Categories

#### 3.1 Retrieval Tests

**Purpose:** Verify correct documents are retrieved.

**Test Cases:**

1. **Exact Match Retrieval** (VRN search)
   ```
   Query: "231-D-54321"
   Expected: Vehicle Registration Certificate, Insurance docs for this VRN
   Metric: Should retrieve in top 3 results
   ```

2. **Semantic Retrieval** (Natural language)
   ```
   Query: "Tell me about the Ford Transit van"
   Expected: Documents mentioning Ford Transit
   Metric: Top result should be relevant (similarity > 0.6)
   ```

3. **Entity-based Retrieval**
   ```
   Query: "What vehicles does Murphy Builders Ltd own?"
   Expected: All documents for this owner
   Metric: Recall should be 100% (find all relevant docs)
   ```

4. **Aggregation Support**
   ```
   Query: "How many cars we have?"
   Expected: All vehicle registration documents
   Metric: Must retrieve ALL vehicle docs (not filter by relevance)
   ```

**Metrics:**
- **Context Precision**: Are relevant docs ranked higher?
- **Context Recall**: Are all relevant docs retrieved?
- **Top-K Accuracy**: Is the answer in top K results?

#### 3.2 Faithfulness Tests

**Purpose:** Verify answers are grounded in retrieved documents.

**Test Cases:**

1. **Factual Grounding**
   ```
   Query: "What is the VIN number for 231-D-54321?"
   Retrieved Context: "VIN Number: YV2AG20C8DA456789"
   Generated Answer: "The VIN number is YV2AG20C8DA456789"
   Expected: Faithfulness score > 0.8
   ```

2. **Hallucination Detection**
   ```
   Query: "What is the color of the Ford Transit?"
   Retrieved Context: (No color information)
   Generated Answer: "I don't have information about the vehicle color"
   Expected: Faithfulness score > 0.9 (no made-up facts)
   ```

**Metrics:**
- **Faithfulness Score** (Ragas): % of statements in answer supported by context
- **Hallucination Rate**: % of answers containing unsupported claims

#### 3.3 Relevance Tests

**Purpose:** Verify answers actually address the question.

**Test Cases:**

1. **Direct Answer**
   ```
   Query: "When does the insurance expire for 231-D-54321?"
   Expected Answer: Should contain a specific date
   Relevance: High (directly answers question)
   ```

2. **Aggregation Answer**
   ```
   Query: "How many vehicles are registered?"
   Expected Answer: Should contain a count (e.g., "4 vehicles")
   Relevance: High (provides the count)
   ```

**Metrics:**
- **Answer Relevancy** (Ragas): Does answer address the question?
- **Answer Correctness** (Ragas): Semantic + factual similarity to ground truth

#### 3.4 Negative Tests (Out-of-Domain)

**Purpose:** Ensure system gracefully handles irrelevant queries.

**Test Cases:**

1. **Unrelated Topic**
   ```
   Query: "What is the biggest river in USA?"
   Expected: "I don't have information about that" or similar
   Should NOT: Hallucinate an answer
   ```

2. **No Matching Documents**
   ```
   Query: "Tell me about Tesla Model 3"
   Expected: "I don't have information about Tesla Model 3"
   Should NOT: Return irrelevant vehicle info
   ```

**Metrics:**
- **Rejection Accuracy**: % of out-of-domain queries correctly rejected
- **False Positive Rate**: % of irrelevant answers for irrelevant queries

### Phase 4: Performance Benchmarks

**Latency Tests:**
- Simple query: < 3s
- Complex query: < 10s
- Aggregation query: < 15s

**Quality Benchmarks:**
- Retrieval Precision@5: > 80%
- Answer Faithfulness: > 85%
- Answer Relevancy: > 90%
- Aggregation Accuracy: > 95%

### Phase 5: Regression Testing

**Baseline Capture:**
```bash
python dev_tools/tests/rag_evaluation/capture_baseline.py
```

Creates `dev_tools/benchmarks/baseline_results.json`:
```json
{
  "date": "2025-11-08",
  "commit": "abc123",
  "metrics": {
    "context_precision": 0.82,
    "faithfulness": 0.87,
    "answer_relevancy": 0.91,
    "latency_p50": 3.2,
    "latency_p95": 8.5
  }
}
```

**Regression Detection:**
- Run before/after major changes
- Alert if metrics drop > 5%
- Track trends over time

## Execution Workflow

### Daily Smoke Tests (Quick)

```bash
# Run quick sanity checks
python dev_tools/tests/rag_evaluation/smoke_test.py
```

**Tests:**
- 5 core queries (VRN, entity, aggregation)
- Verify API is running
- Check basic retrieval
- < 1 minute execution

### Weekly Full Suite (Comprehensive)

```bash
# Run complete test suite
python dev_tools/tests/rag_evaluation/run_full_suite.py
```

**Tests:**
- All ground truth queries (50+)
- Synthetic test set (100+)
- Performance benchmarks
- Regression checks
- ~30 minutes execution

### Pre-deployment Validation (Critical)

```bash
# Run before any production deployment
python dev_tools/tests/rag_evaluation/pre_deployment.py
```

**Tests:**
- Critical path queries (must pass 100%)
- Regression detection
- Performance verification
- Safety checks (hallucination, rejection)

## Test Implementation Patterns

### Pattern 1: Retrieval Test

```python
def test_retrieval_quality(query, expected_docs):
    """Test retrieval returns correct documents"""
    results = retriever.retrieve(query, top_k=10)

    # Check if expected docs are in top K
    retrieved_files = [r.filename for r in results]

    for expected_doc in expected_docs:
        assert expected_doc in retrieved_files[:5], \
            f"Expected doc '{expected_doc}' not in top 5"

    # Check relevance scores
    assert results[0].similarity_score > 0.6, \
        "Top result relevance too low"
```

### Pattern 2: Faithfulness Test

```python
def test_answer_faithfulness(query, expected_ground_truth):
    """Test answer is faithful to retrieved context"""
    response = rag_pipeline.query(query)

    # Use Ragas faithfulness metric
    from ragas.metrics import Faithfulness

    faithfulness = Faithfulness()
    score = faithfulness.score(
        question=query,
        answer=response.answer,
        contexts=response.source_nodes
    )

    assert score > 0.8, f"Faithfulness too low: {score}"
```

### Pattern 3: Aggregation Test

```python
def test_aggregation_query():
    """Test system handles aggregation queries"""
    query = "How many vehicles do we have?"

    # Step 1: Verify retrieval gets ALL vehicle docs
    retrieved = retriever.retrieve(query, top_k=50)
    vehicle_docs = [r for r in retrieved if 'vehicle' in r.content.lower()]

    assert len(vehicle_docs) >= 4, \
        "Not all vehicle docs retrieved for aggregation"

    # Step 2: Verify reranker doesn't filter them out
    reranked = reranker.rerank(query, retrieved, top_k=20)

    assert len(reranked) >= 4, \
        "Reranker filtered out vehicle docs"

    # Step 3: Verify answer contains count
    response = rag_pipeline.query(query)

    assert any(word in response.answer.lower() for word in ['four', '4']), \
        "Answer doesn't contain vehicle count"
```

### Pattern 4: Negative Test

```python
def test_out_of_domain_rejection():
    """Test system rejects irrelevant queries"""
    query = "What is the biggest river in USA?"

    response = rag_pipeline.query(query)

    # Should not provide a confident answer
    rejection_phrases = [
        "don't have information",
        "cannot find",
        "not available in documents"
    ]

    assert any(phrase in response.answer.lower() for phrase in rejection_phrases), \
        "System hallucinated answer for out-of-domain query"

    # Confidence should be low
    assert response.confidence < 0.5, \
        f"Confidence too high for out-of-domain: {response.confidence}"
```

## Monitoring and Alerts

### Real-time Metrics (Production)

Track in production:
- Query latency (p50, p95, p99)
- Retrieval success rate
- Answer generation rate
- Error rate by query type

### Quality Metrics Dashboard

Visualize over time:
- Faithfulness trend
- Relevancy trend
- Rejection accuracy
- User feedback (if available)

### Alerts

Trigger alerts when:
- Error rate > 5%
- Latency p95 > 15s
- Faithfulness drops > 10%
- Retrieval fails > 10% queries

## Best Practices

1. **Start with Real Data**: Use actual documents from database
2. **Mix Manual + Synthetic**: Combine human-verified and AI-generated tests
3. **Test Edge Cases**: Aggregation, multi-document, out-of-domain
4. **Track Baselines**: Measure before/after changes
5. **Automate Everything**: Run tests in CI/CD
6. **Monitor Production**: Real-world queries reveal issues
7. **Iterate Ground Truth**: Update as system improves

## Common Issues and Solutions

### Issue: Low Retrieval Recall

**Symptom:** Missing relevant documents in results

**Debug:**
```bash
python dev_tools/tests/rag_evaluation/debug_retrieval.py --query "your query"
```

**Solutions:**
- Lower similarity threshold
- Increase top_k
- Check chunking strategy
- Verify embeddings quality

### Issue: Hallucination

**Symptom:** Answers contain unsupported claims

**Debug:**
- Check Faithfulness score
- Review retrieved contexts
- Inspect answer generation prompt

**Solutions:**
- Strengthen "stick to context" in prompt
- Add citation requirements
- Lower temperature for LLM

### Issue: Aggregation Failures

**Symptom:** "How many" queries fail

**Debug:**
- Check if reranker filters results
- Verify all docs reach answer generation

**Solution:**
- Disable score-based filtering in reranker (✅ Fixed)
- Use top_n selection instead

## Next Steps

1. ✅ Read this guide
2. 📝 Create initial ground truth dataset (10-20 queries)
3. 🧪 Run existing tests as baseline
4. 🔧 Implement Ragas evaluation scripts
5. 📊 Set up monitoring dashboard
6. 🔄 Iterate and improve
