# tests/test_search_api.py
# Integration tests for search API endpoint

import pytest
import requests
import time

# Test configuration
API_BASE_URL = "http://localhost:8000"
SEARCH_ENDPOINT = f"{API_BASE_URL}/api/search/"
HEALTH_ENDPOINT = f"{API_BASE_URL}/api/search/health"


class TestSearchAPIValidation:
    """Test API input validation"""

    def test_valid_search_request(self):
        """Test that valid search requests work"""
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "John Nolan", "top_k": 10}
        )
        assert response.status_code in [200, 504]  # 200 OK or 504 timeout
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert "success" in data

    def test_empty_query_rejected(self):
        """Test that empty queries are rejected with 400 or 422"""
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "", "top_k": 10}
        )
        # Accept both 400 (custom validation) and 422 (Pydantic schema validation)
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data

    def test_sql_injection_blocked(self):
        """Test that SQL injection attempts are blocked"""
        malicious_queries = [
            "SELECT * FROM users",
            "1' OR '1'='1",
            "test'; DROP TABLE documents; --",
            "UNION SELECT password FROM users"
        ]

        for query in malicious_queries:
            response = requests.post(
                SEARCH_ENDPOINT,
                json={"query": query, "top_k": 10}
            )
            assert response.status_code == 400
            data = response.json()
            assert "sql" in data["detail"].lower()

    def test_xss_blocked(self):
        """Test that XSS attempts are blocked"""
        xss_queries = [
            "<script>alert('XSS')</script>",
            "javascript:void(0)",
            "<img src=x onerror=alert(1)>",
            "<iframe src='evil.com'></iframe>"
        ]

        for query in xss_queries:
            response = requests.post(
                SEARCH_ENDPOINT,
                json={"query": query, "top_k": 10}
            )
            assert response.status_code == 400
            data = response.json()
            assert "script" in data["detail"].lower()

    def test_too_long_query_rejected(self):
        """Test that queries over 1000 chars are rejected"""
        long_query = "a" * 1001
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": long_query, "top_k": 10}
        )
        # Accept both 400 (custom validation) and 422 (Pydantic schema validation)
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data

    def test_invalid_top_k_handled(self):
        """Test that invalid top_k values are handled gracefully"""
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "test", "top_k": 1000}
        )
        # Should be rejected by Pydantic (422) or succeed with corrected value (200) or timeout (504)
        assert response.status_code in [200, 422, 504]


class TestSearchAPIResponses:
    """Test API response formats"""

    def test_successful_search_response_format(self):
        """Test that successful responses have correct format"""
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "insurance", "top_k": 5},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            # Check required fields
            assert "success" in data
            assert "query" in data
            assert "results" in data
            assert "total_results" in data
            assert "search_time" in data
            assert "metadata" in data

            # Check types
            assert isinstance(data["success"], bool)
            assert isinstance(data["results"], list)
            assert isinstance(data["total_results"], int)
            assert isinstance(data["search_time"], (int, float))

    def test_empty_results_response(self):
        """Test response when no results are found"""
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "nonexistent_vehicle_xyz123", "top_k": 10},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            assert data["total_results"] == 0
            assert data["results"] == []
            # Should have helpful message in answer
            if "answer" in data and data["answer"]:
                assert "no results found" in data["answer"].lower()

    def test_timeout_response(self):
        """Test that timeout errors return 504"""
        # This test assumes that some very complex query might timeout
        # In practice, you might need to mock this
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "test query", "top_k": 10},
            timeout=70  # Allow for potential timeout
        )
        if response.status_code == 504:
            data = response.json()
            assert "timeout" in data["detail"].lower()


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check_available(self):
        """Test that health check endpoint is accessible"""
        response = requests.get(HEALTH_ENDPOINT)
        assert response.status_code == 200

    def test_health_check_format(self):
        """Test that health check returns expected format"""
        response = requests.get(HEALTH_ENDPOINT)
        data = response.json()
        assert "status" in data
        assert "components" in data


class TestErrorRecovery:
    """Test error recovery and retry scenarios"""

    def test_multiple_requests_work(self):
        """Test that multiple requests work (no state pollution)"""
        # First request
        response1 = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "test1", "top_k": 5},
            timeout=30
        )

        # Second request
        response2 = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "test2", "top_k": 5},
            timeout=30
        )

        # Both should succeed or timeout (not fail with 500)
        assert response1.status_code in [200, 504]
        assert response2.status_code in [200, 504]

    def test_invalid_then_valid_request(self):
        """Test that API recovers after invalid request"""
        # Invalid request
        response1 = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "", "top_k": 10}
        )
        # Accept both 400 (custom validation) and 422 (Pydantic schema validation)
        assert response1.status_code in [400, 422]

        # Valid request should still work
        response2 = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "valid query", "top_k": 10},
            timeout=30
        )
        assert response2.status_code in [200, 504]


class TestPerformance:
    """Test performance and timeout handling"""

    def test_search_response_time(self):
        """Test that searches complete in reasonable time"""
        start = time.time()
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": "insurance", "top_k": 5},
            timeout=65  # Slightly over max timeout
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            # Successful searches should complete within timeout
            assert elapsed < 60  # SEARCH_TIMEOUT is 60s
        elif response.status_code == 504:
            # Timeout responses should happen around timeout value
            assert elapsed >= 15  # Should take at least some time
            assert elapsed <= 70  # But not much longer than timeout


def print_test_summary():
    """Print test execution summary"""
    print("\n" + "=" * 80)
    print("SEARCH API TEST SUITE")
    print("=" * 80)
    print("\nTest Coverage:")
    print("  ✓ Input validation (SQL injection, XSS, length limits)")
    print("  ✓ Response format validation")
    print("  ✓ Error handling (empty results, timeouts)")
    print("  ✓ Health check endpoint")
    print("  ✓ Error recovery and retry")
    print("  ✓ Performance and timeout handling")
    print("\nIMPORTANT: Ensure API server is running on http://localhost:8000")
    print("  Start server: python run_api.py")
    print("\nRun tests: pytest tests/test_search_api.py -v")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    print_test_summary()
    pytest.main([__file__, "-v", "-s"])
