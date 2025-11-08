# api/core/validators.py
# Input validation and sanitization utilities

import re
from typing import Tuple
from fastapi import HTTPException


class QueryValidator:
    """Validates and sanitizes search queries"""

    # Dangerous patterns that could indicate injection attacks
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\;|\/\*|\*\/)",
        r"(\bOR\b.*=.*|AND\b.*=.*)",
        r"(UNION\s+SELECT)",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
    ]

    # Maximum allowed lengths
    MAX_QUERY_LENGTH = 1000
    MIN_QUERY_LENGTH = 1
    MAX_TOP_K = 50
    MIN_TOP_K = 1

    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, str, str]:
        """
        Validate and sanitize search query

        Returns:
            Tuple[is_valid, sanitized_query, error_message]
        """
        if not query:
            return False, "", "Query cannot be empty"

        # Check length
        if len(query) < cls.MIN_QUERY_LENGTH:
            return False, "", f"Query too short (minimum {cls.MIN_QUERY_LENGTH} character)"

        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, "", f"Query too long (maximum {cls.MAX_QUERY_LENGTH} characters)"

        # Strip whitespace
        query = query.strip()

        if not query:
            return False, "", "Query cannot be empty or whitespace only"

        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "", "Query contains potentially dangerous SQL patterns"

        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "", "Query contains potentially dangerous script patterns"

        # Check for excessive special characters (potential attack)
        special_char_count = sum(1 for c in query if not c.isalnum() and not c.isspace() and c not in "-_.,?!'\"")
        if special_char_count > len(query) * 0.3:  # More than 30% special chars
            return False, "", "Query contains too many special characters"

        # Sanitize: remove multiple spaces
        sanitized = re.sub(r'\s+', ' ', query).strip()

        return True, sanitized, ""

    @classmethod
    def validate_top_k(cls, top_k: int) -> Tuple[bool, int, str]:
        """
        Validate top_k parameter

        Returns:
            Tuple[is_valid, sanitized_value, error_message]
        """
        if top_k < cls.MIN_TOP_K:
            return False, cls.MIN_TOP_K, f"top_k must be at least {cls.MIN_TOP_K}"

        if top_k > cls.MAX_TOP_K:
            return False, cls.MAX_TOP_K, f"top_k cannot exceed {cls.MAX_TOP_K}"

        return True, top_k, ""

    @classmethod
    def validate_similarity_threshold(cls, threshold: float) -> Tuple[bool, float, str]:
        """
        Validate similarity threshold

        Returns:
            Tuple[is_valid, sanitized_value, error_message]
        """
        if threshold < 0.0:
            return False, 0.0, "Similarity threshold cannot be negative"

        if threshold > 1.0:
            return False, 1.0, "Similarity threshold cannot exceed 1.0"

        return True, threshold, ""


class ErrorMessageFormatter:
    """Formats technical errors into user-friendly messages"""

    @staticmethod
    def format_error(error: Exception, user_friendly: bool = True) -> str:
        """
        Format error message for user display

        Args:
            error: The exception that occurred
            user_friendly: If True, return simplified message. If False, return technical details.

        Returns:
            Formatted error message
        """
        error_str = str(error)
        error_type = type(error).__name__

        if not user_friendly:
            return f"{error_type}: {error_str}"

        # Map technical errors to user-friendly messages
        if "connection" in error_str.lower() or "timeout" in error_str.lower():
            return "Unable to connect to the database. Please try again in a moment."

        if "embedding" in error_str.lower() or "gemini" in error_str.lower():
            return "AI service temporarily unavailable. Please try again shortly."

        if "validation" in error_str.lower():
            return f"Invalid input: {error_str}"

        if "not found" in error_str.lower():
            return "The requested resource was not found."

        if "unauthorized" in error_str.lower() or "forbidden" in error_str.lower():
            return "You don't have permission to perform this action."

        # Default user-friendly message
        return "An unexpected error occurred. Our team has been notified. Please try again later."

    @staticmethod
    def format_empty_results_message(query: str) -> str:
        """Generate helpful message when no results are found"""
        return (
            f"No results found for '{query}'. "
            "Try:\n"
            "• Using different keywords\n"
            "• Checking spelling\n"
            "• Using more general terms\n"
            "• Searching for vehicle registration numbers (e.g., '191-D-12345')"
        )
