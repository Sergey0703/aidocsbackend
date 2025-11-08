# tests/test_validators.py
# Unit tests for input validators

import sys
import os
# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from api.core.validators import QueryValidator, ErrorMessageFormatter


class TestQueryValidator:
    """Test QueryValidator functionality"""

    def test_valid_simple_query(self):
        """Test that simple valid queries pass validation"""
        is_valid, sanitized, error = QueryValidator.validate_query("John Nolan")
        assert is_valid == True
        assert sanitized == "John Nolan"
        assert error == ""

    def test_valid_vrn_query(self):
        """Test that VRN queries pass validation"""
        is_valid, sanitized, error = QueryValidator.validate_query("191-D-12345")
        assert is_valid == True
        assert sanitized == "191-D-12345"
        assert error == ""

    def test_valid_query_with_safe_special_chars(self):
        """Test that queries with safe special characters pass"""
        is_valid, sanitized, error = QueryValidator.validate_query("insurance documents, please!")
        assert is_valid == True
        assert "insurance documents" in sanitized
        assert error == ""

    def test_empty_query(self):
        """Test that empty queries are rejected"""
        is_valid, sanitized, error = QueryValidator.validate_query("")
        assert is_valid == False
        assert "cannot be empty" in error.lower()

    def test_whitespace_only_query(self):
        """Test that whitespace-only queries are rejected"""
        is_valid, sanitized, error = QueryValidator.validate_query("   ")
        assert is_valid == False
        assert "empty" in error.lower()

    def test_too_long_query(self):
        """Test that queries exceeding max length are rejected"""
        long_query = "a" * 1001
        is_valid, sanitized, error = QueryValidator.validate_query(long_query)
        assert is_valid == False
        assert "too long" in error.lower()
        assert "1000" in error

    def test_sql_injection_select(self):
        """Test that SQL SELECT statements are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("SELECT * FROM users")
        assert is_valid == False
        assert "sql" in error.lower()

    def test_sql_injection_drop(self):
        """Test that SQL DROP statements are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("test'; DROP TABLE documents; --")
        assert is_valid == False
        assert "sql" in error.lower()

    def test_sql_injection_union(self):
        """Test that UNION attacks are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("1' UNION SELECT password FROM users--")
        assert is_valid == False
        assert "sql" in error.lower()

    def test_sql_injection_or_attack(self):
        """Test that OR-based SQL injection is blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("1' OR '1'='1")
        assert is_valid == False
        assert "sql" in error.lower()

    def test_xss_script_tag(self):
        """Test that script tags are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("<script>alert('XSS')</script>")
        assert is_valid == False
        assert "script" in error.lower()

    def test_xss_javascript_url(self):
        """Test that javascript: URLs are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("javascript:void(0)")
        assert is_valid == False
        assert "script" in error.lower()

    def test_xss_event_handler(self):
        """Test that event handlers are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("<img src=x onerror=alert(1)>")
        assert is_valid == False
        assert "script" in error.lower()

    def test_xss_iframe(self):
        """Test that iframe tags are blocked"""
        is_valid, sanitized, error = QueryValidator.validate_query("<iframe src='evil.com'></iframe>")
        assert is_valid == False
        assert "script" in error.lower()

    def test_excessive_special_characters(self):
        """Test that queries with too many special characters are rejected"""
        is_valid, sanitized, error = QueryValidator.validate_query("!!!!!!!!!!!!!!!!!!!!!!!!!")
        assert is_valid == False
        assert "special characters" in error.lower()

    def test_multiple_spaces_sanitization(self):
        """Test that multiple spaces are collapsed to single spaces"""
        is_valid, sanitized, error = QueryValidator.validate_query("query   with    spaces")
        assert is_valid == True
        assert "query with spaces" == sanitized

    def test_leading_trailing_spaces_sanitization(self):
        """Test that leading/trailing spaces are removed"""
        is_valid, sanitized, error = QueryValidator.validate_query("  query  ")
        assert is_valid == True
        assert sanitized == "query"


class TestTopKValidator:
    """Test top_k parameter validation"""

    def test_valid_top_k(self):
        """Test that valid top_k values pass"""
        is_valid, sanitized, error = QueryValidator.validate_top_k(10)
        assert is_valid == True
        assert sanitized == 10
        assert error == ""

    def test_top_k_at_min_boundary(self):
        """Test top_k at minimum boundary (1)"""
        is_valid, sanitized, error = QueryValidator.validate_top_k(1)
        assert is_valid == True
        assert sanitized == 1

    def test_top_k_at_max_boundary(self):
        """Test top_k at maximum boundary (50)"""
        is_valid, sanitized, error = QueryValidator.validate_top_k(50)
        assert is_valid == True
        assert sanitized == 50

    def test_top_k_below_min(self):
        """Test that top_k below minimum is rejected"""
        is_valid, sanitized, error = QueryValidator.validate_top_k(0)
        assert is_valid == False
        assert "at least 1" in error.lower()

    def test_top_k_above_max(self):
        """Test that top_k above maximum is rejected"""
        is_valid, sanitized, error = QueryValidator.validate_top_k(100)
        assert is_valid == False
        assert "cannot exceed 50" in error.lower()


class TestSimilarityThresholdValidator:
    """Test similarity_threshold parameter validation"""

    def test_valid_threshold(self):
        """Test that valid thresholds pass"""
        is_valid, sanitized, error = QueryValidator.validate_similarity_threshold(0.5)
        assert is_valid == True
        assert sanitized == 0.5
        assert error == ""

    def test_threshold_at_min_boundary(self):
        """Test threshold at minimum boundary (0.0)"""
        is_valid, sanitized, error = QueryValidator.validate_similarity_threshold(0.0)
        assert is_valid == True
        assert sanitized == 0.0

    def test_threshold_at_max_boundary(self):
        """Test threshold at maximum boundary (1.0)"""
        is_valid, sanitized, error = QueryValidator.validate_similarity_threshold(1.0)
        assert is_valid == True
        assert sanitized == 1.0

    def test_threshold_below_min(self):
        """Test that negative thresholds are rejected"""
        is_valid, sanitized, error = QueryValidator.validate_similarity_threshold(-0.5)
        assert is_valid == False
        assert "cannot be negative" in error.lower()

    def test_threshold_above_max(self):
        """Test that thresholds above 1.0 are rejected"""
        is_valid, sanitized, error = QueryValidator.validate_similarity_threshold(1.5)
        assert is_valid == False
        assert "cannot exceed 1.0" in error.lower()


class TestErrorMessageFormatter:
    """Test ErrorMessageFormatter functionality"""

    def test_connection_error_formatting(self):
        """Test that connection errors are formatted user-friendly"""
        error = Exception("Connection timeout to database")
        message = ErrorMessageFormatter.format_error(error, user_friendly=True)
        assert "database" in message.lower()
        assert "try again" in message.lower()

    def test_embedding_error_formatting(self):
        """Test that embedding/Gemini errors are formatted user-friendly"""
        error = Exception("Gemini API rate limit exceeded")
        message = ErrorMessageFormatter.format_error(error, user_friendly=True)
        assert "ai service" in message.lower() or "temporarily unavailable" in message.lower()

    def test_validation_error_formatting(self):
        """Test that validation errors show details"""
        error = Exception("validation failed: query too long")
        message = ErrorMessageFormatter.format_error(error, user_friendly=True)
        assert "invalid input" in message.lower()

    def test_generic_error_formatting(self):
        """Test that generic errors have user-friendly message"""
        error = Exception("NoneType object has no attribute 'filename'")
        message = ErrorMessageFormatter.format_error(error, user_friendly=True)
        assert "unexpected error" in message.lower()
        assert "try again later" in message.lower()

    def test_technical_error_formatting(self):
        """Test that technical mode shows full error details"""
        error = ValueError("Invalid chunk index: -1")
        message = ErrorMessageFormatter.format_error(error, user_friendly=False)
        assert "ValueError" in message
        assert "Invalid chunk index" in message

    def test_empty_results_message(self):
        """Test empty results message formatting"""
        message = ErrorMessageFormatter.format_empty_results_message("nonexistent_vehicle")
        assert "No results found" in message
        assert "nonexistent_vehicle" in message
        assert "Try:" in message or "try" in message.lower()


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_unicode_query(self):
        """Test that unicode characters are handled correctly"""
        is_valid, sanitized, error = QueryValidator.validate_query("café résumé")
        assert is_valid == True
        assert "café" in sanitized

    def test_emoji_query(self):
        """Test that emojis in queries are handled"""
        is_valid, sanitized, error = QueryValidator.validate_query("car 🚗 insurance")
        # Should either pass or fail gracefully
        assert isinstance(is_valid, bool)

    def test_numbers_only_query(self):
        """Test that numeric-only queries are valid"""
        is_valid, sanitized, error = QueryValidator.validate_query("123456")
        assert is_valid == True

    def test_mixed_case_sql_injection(self):
        """Test that mixed-case SQL injection is caught"""
        is_valid, sanitized, error = QueryValidator.validate_query("SeLeCt * FrOm users")
        assert is_valid == False
        assert "sql" in error.lower()

    def test_query_at_exact_max_length(self):
        """Test query at exactly max length (1000 chars)"""
        query = "a" * 1000
        is_valid, sanitized, error = QueryValidator.validate_query(query)
        assert is_valid == True

    def test_query_one_over_max_length(self):
        """Test query one character over max length"""
        query = "a" * 1001
        is_valid, sanitized, error = QueryValidator.validate_query(query)
        assert is_valid == False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
