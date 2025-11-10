# RAG System Tests

Comprehensive test suite for error handling, input validation, and security features.

## Test Structure

```
tests/
├── test_validators.py                      # Unit tests for input validators
├── test_search_api.py                      # Integration tests for API endpoints
├── generate_complex_test_document.py       # Generate complex DOCX test document
├── test_complex_document_processing.py     # Full pipeline validation (conversion → indexing → search)
├── test_data/                              # Test documents directory
│   └── Vehicle_Service_Report_Toyota_Camry_2023.docx  # Complex test document (38.4 KB)
└── README.md                                # This file
```

## Prerequisites

### Install Test Dependencies

```bash
pip install pytest requests
```

### For API Integration Tests

The API server must be running:

```bash
python run_api.py
```

## Running Tests

### Quick Start - All Tests

```bash
python run_tests.py
```

This runs:
1. Validator unit tests (no API required)
2. API integration tests (requires API running)
3. Displays summary

### Specific Test Suites

**Validator Tests Only** (no API required):
```bash
python run_tests.py validators
```

**API Integration Tests** (requires API):
```bash
python run_tests.py api
```

**Quick Security Check** (requires API):
```bash
python run_tests.py security
```

### Using pytest Directly

**All tests:**
```bash
pytest tests/ -v
```

**Specific test file:**
```bash
pytest tests/test_validators.py -v
```

**Specific test class:**
```bash
pytest tests/test_validators.py::TestQueryValidator -v
```

**Specific test method:**
```bash
pytest tests/test_validators.py::TestQueryValidator::test_sql_injection_select -v
```

## Test Coverage

### Validator Unit Tests (`test_validators.py`)

#### QueryValidator Tests
- ✅ Valid queries (simple, VRN, with safe special chars)
- ✅ Empty and whitespace-only queries
- ✅ Length validation (too short, too long, at boundaries)
- ✅ SQL Injection protection:
  - SELECT statements
  - DROP/DELETE statements
  - UNION attacks
  - OR-based attacks
- ✅ XSS protection:
  - Script tags
  - JavaScript URLs
  - Event handlers
  - Iframe tags
- ✅ Special character limits
- ✅ Input sanitization (spaces, trimming)

#### TopK Validator Tests
- ✅ Valid values
- ✅ Boundary testing (min=1, max=50)
- ✅ Out of range values

#### SimilarityThreshold Validator Tests
- ✅ Valid thresholds
- ✅ Boundary testing (0.0 to 1.0)
- ✅ Out of range values

#### ErrorMessageFormatter Tests
- ✅ Connection error formatting
- ✅ Embedding/AI service error formatting
- ✅ Validation error formatting
- ✅ Generic error formatting
- ✅ Technical vs user-friendly modes
- ✅ Empty results message generation

#### Edge Cases
- ✅ Unicode characters
- ✅ Emoji handling
- ✅ Numbers-only queries
- ✅ Mixed-case SQL injection
- ✅ Exact boundary values

### API Integration Tests (`test_search_api.py`)

#### Input Validation Tests
- ✅ Valid search requests
- ✅ Empty query rejection
- ✅ SQL injection blocking
- ✅ XSS blocking
- ✅ Long query rejection
- ✅ Invalid top_k handling

#### Response Format Tests
- ✅ Successful response structure
- ✅ Required fields validation
- ✅ Data type validation
- ✅ Empty results response
- ✅ Timeout response format

#### Health Check Tests
- ✅ Endpoint availability
- ✅ Response format

#### Error Recovery Tests
- ✅ Multiple sequential requests
- ✅ Recovery after invalid request
- ✅ No state pollution

#### Performance Tests
- ✅ Response time validation
- ✅ Timeout handling

## Expected Results

### Successful Test Run

```
======================== test session starts ========================
tests/test_validators.py::TestQueryValidator::test_valid_simple_query PASSED
tests/test_validators.py::TestQueryValidator::test_sql_injection_select PASSED
tests/test_validators.py::TestQueryValidator::test_xss_script_tag PASSED
...
======================== 45 passed in 2.5s ==========================

API INTEGRATION TESTS
✓ API server is running on http://localhost:8000
tests/test_search_api.py::TestSearchAPIValidation::test_sql_injection_blocked PASSED
tests/test_search_api.py::TestSearchAPIValidation::test_xss_blocked PASSED
...
======================== 18 passed in 15.2s =========================

TEST SUMMARY
Validator Unit Tests: ✅ PASSED
API Integration Tests: ✅ PASSED

🎉 ALL TESTS PASSED!
```

### Security Validation Results

```
QUICK SECURITY VALIDATION
Testing common attack vectors...

  ✓ SQL Injection: BLOCKED (400)
  ✓ XSS Attack: BLOCKED (400)
  ✓ Long Input: BLOCKED (400)
  ✓ Empty Query: BLOCKED (400)

✅ All attack vectors blocked successfully!
```

## Test Scenarios

### Security Tests

**SQL Injection Patterns Tested:**
```python
"SELECT * FROM users"
"1' OR '1'='1"
"test'; DROP TABLE documents; --"
"UNION SELECT password FROM users"
```

**XSS Patterns Tested:**
```python
"<script>alert('XSS')</script>"
"javascript:void(0)"
"<img src=x onerror=alert(1)>"
"<iframe src='evil.com'></iframe>"
```

**Input Validation:**
- Empty strings
- Whitespace-only
- 1001+ character strings
- Excessive special characters (>30%)

### Functional Tests

**Valid Queries:**
```python
"John Nolan"           # Simple name
"191-D-12345"          # VRN format
"insurance documents"  # Multi-word
"café résumé"          # Unicode
```

**Edge Cases:**
```python
"query   with    spaces"  # Multiple spaces → sanitized
"  leading spaces  "      # Trimmed
"123456"                  # Numbers only
"a" * 1000                # Exactly at limit
```

## Troubleshooting

### API Tests Fail with "Connection Refused"

**Problem:** API server not running

**Solution:**
```bash
# Start API server in separate terminal
python run_api.py

# Then run tests
python run_tests.py
```

### Import Errors

**Problem:** Missing dependencies

**Solution:**
```bash
pip install pytest requests
```

### Tests Timeout

**Problem:** API operations taking too long

**Solution:**
- Check database connection
- Verify Gemini API key is valid
- Check network connectivity
- Review timeout settings in `api/modules/search/routes/search.py`

### Some Tests Fail

**Problem:** Implementation issues

**Solution:**
1. Review test output for specific failures
2. Check logs in `python run_api.py` terminal
3. Verify `.env` configuration
4. Run individual failing test for details:
   ```bash
   pytest tests/test_validators.py::TestQueryValidator::test_sql_injection_select -v
   ```

## Writing New Tests

### Adding Validator Tests

```python
def test_new_validation_rule(self):
    """Test description"""
    is_valid, sanitized, error = QueryValidator.validate_query("test input")
    assert is_valid == True
    assert sanitized == "expected output"
```

### Adding API Tests

```python
def test_new_api_behavior(self):
    """Test description"""
    response = requests.post(
        SEARCH_ENDPOINT,
        json={"query": "test", "top_k": 10},
        timeout=30
    )
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest requests

# Start API in background
python run_api.py &
API_PID=$!

# Wait for API to start
sleep 5

# Run tests
python run_tests.py

# Cleanup
kill $API_PID
```

## Coverage Report

To generate coverage report:

```bash
pip install pytest-cov

# Run with coverage
pytest tests/ --cov=api/core --cov-report=html

# View report
open htmlcov/index.html
```

## Complex Document Processing Tests (NEW - API-BASED)

### Purpose

End-to-end validation of the PRODUCTION RAG pipeline using a realistic vehicle service report document.

**Tests the complete workflow:**
1. Upload PDF via API → Supabase Storage
2. Trigger conversion (Docling) → Markdown + JSON
3. Trigger indexing → Chunks + embeddings in database
4. Test search quality → Verify RAG retrieval

### Test Document: Vehicle Service Report

**Generated file:** `tests/test_data/Vehicle_Service_Report_Toyota_Camry_2023.docx` (38.4 KB, 4 pages)

**Structure:**
- **Page 1:** Headers, formatting (bold/italic), vehicle info (191-D-12345), bulleted lists
- **Page 2:** Large table (16 rows × 6 columns) - **CRITICAL for chunking test**
- **Page 3:** Image with text (VIN plate for OCR testing)
- **Page 4:** Nested headings, cost breakdown table, totals

### Prerequisites

1. **Start API server:**
   ```bash
   python run_api.py
   ```

2. **Configure HybridChunker:**
   - Set `USE_HYBRID_CHUNKING=true` in `rag_indexer/.env`
   - Set `SAVE_JSON_OUTPUT=true` in `rag_indexer/.env`

3. **Generate and convert test document:**
   ```bash
   # Generate DOCX
   python tests/generate_complex_test_document.py

   # Open DOCX and Save As PDF (manual step in Word)
   # File -> Save As -> PDF
   # Save to: tests/test_data/Vehicle_Service_Report_Toyota_Camry_2023.pdf
   ```

### Running the Test

```bash
# Run complete API-based test
python tests/test_complex_document_processing.py
```

**Test workflow:**
1. **Upload:** POST to `/api/documents/upload` → file to Supabase Storage
2. **Conversion:** POST to `/api/conversion/start` → Docling processing
3. **Indexing:** POST to `/api/indexing/start` → chunking + embeddings
4. **Search:** POST to `/api/search` → test 6 queries

**Expected duration:** ~5-10 minutes (depending on Gemini API speed)

### Test Coverage

**Automated Tests:**

1. **Upload to Supabase Storage**
   - File uploaded via `/api/documents/upload`
   - Registry entry created in `document_registry`
   - Storage path: `raw/pending/{filename}`
   - Duplicate detection working (file hash comparison)

2. **Document Conversion** (Docling via API)
   - Triggered via `/api/conversion/start`
   - Status polling until completion
   - Markdown + JSON created in Storage
   - Bold/italic formatting preserved (`**text**`, `*text*`)
   - Tables preserved in Markdown format
   - OCR for images (Gemini Vision API)

3. **Indexing** (Chunking + Embeddings via API)
   - Triggered via `/api/indexing/start`
   - Status polling until completion
   - HybridChunker used (structure-aware)
   - Chunks linked to registry via `registry_id`
   - Embeddings generated (768D Gemini)
   - Metadata includes file_name, chunk_index, headings

4. **Search Quality** (6 automated queries)
   - `"brake pads"` → finds table data (services)
   - `"oil change"` → finds multiple service entries
   - `"191-D-12345"` → finds VRN
   - `"service history"` → finds complete table
   - `"total cost"` → finds €654.98 and €2,785.00
   - `"VIN WF0"` → finds OCR-extracted text

**Quality Checks:**

5. **HybridChunker Quality** (Database validation)
   - Large table NOT split mid-row ✅
   - Heading hierarchy added to chunk content
   - Reasonable chunk count (~10-20, not 50+)
   - Lists kept intact

6. **Frontend Rendering** (Manual validation)
   - Open http://localhost:3000
   - Search for test document
   - Verify `react-markdown` renders formatting
   - No visible `**` or `*` symbols
   - Tables display as HTML tables
   - Bold/italic rendered correctly

### Why This Test Matters

**Problem:** Complex documents (service reports, insurance forms) have tables and structure.
**Risk:** Simple chunking (SentenceSplitter) can split tables mid-row → broken data.
**Solution:** HybridChunker uses JSON (DoclingDocument) to respect document structure.

**Example:**
```markdown
## Service History Table
| Date       | Service     | Cost     |
|------------|-------------|----------|
| 15/01/2025 | Oil Change  | €120.00  |  ← THIS ROW
| 10/12/2024 | Tire Rotate | €45.00   |  ← MUST STAY TOGETHER

SentenceSplitter: Chunk 1 ends here ----^  ❌ BROKEN
HybridChunker:    Keeps entire table ✅ INTACT
```

### Configuration Required

```bash
# In rag_indexer/.env
USE_HYBRID_CHUNKING=true      # Enable structure-aware chunking
SAVE_JSON_OUTPUT=true          # Save DoclingDocument JSON
JSON_OUTPUT_DIR=./data/json    # JSON directory path
```

See [CLAUDE.md](../CLAUDE.md#L277-L407) for detailed explanation of HybridChunker.

## Related Documentation

- [ERROR_HANDLING_IMPROVEMENTS.md](../ERROR_HANDLING_IMPROVEMENTS.md) - Error handling implementation details
- [api/core/validators.py](../api/core/validators.py) - Validator implementation
- [api/modules/search/routes/search.py](../api/modules/search/routes/search.py) - Search endpoint
- [CLAUDE.md](../CLAUDE.md#L277-L407) - HybridChunker vs SentenceSplitter comparison
- [RAG_TESTING_GUIDE.md](../dev_tools/RAG_TESTING_GUIDE.md) - Ragas-based RAG testing

---

**Last Updated:** 2025-11-10
**Test Coverage:** 63+ test cases (including complex document tests)
**Status:** ✅ All tests passing
