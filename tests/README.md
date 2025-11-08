# RAG System Tests

Comprehensive test suite for error handling, input validation, and security features.

## Test Structure

```
tests/
├── test_validators.py      # Unit tests for input validators
├── test_search_api.py       # Integration tests for API endpoints
└── README.md                # This file
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

## Related Documentation

- [ERROR_HANDLING_IMPROVEMENTS.md](../ERROR_HANDLING_IMPROVEMENTS.md) - Error handling implementation details
- [api/core/validators.py](../api/core/validators.py) - Validator implementation
- [api/modules/search/routes/search.py](../api/modules/search/routes/search.py) - Search endpoint

---

**Last Updated:** 2025-11-08
**Test Coverage:** 63 test cases
**Status:** ✅ All tests passing
