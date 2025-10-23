#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_query_preprocessing.py - Test query preprocessing with stop words filtering

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import ProductionRAGConfig
from query_processing.query_preprocessor import QueryPreprocessor


def test_preprocessing():
    """Test query preprocessing with various edge cases"""

    print("\n" + "=" * 80)
    print("QUERY PREPROCESSING TEST SUITE")
    print("=" * 80)

    # Initialize
    config = ProductionRAGConfig()
    preprocessor = QueryPreprocessor(config, enable_ai_enhancement=True)

    # Test cases: (query, expected_behavior, description)
    test_cases = [
        # Stop words - should be rejected or cleaned
        ("the", "REJECTED", "Pure stop word"),
        ("to", "REJECTED", "Pure stop word"),
        ("and", "REJECTED", "Pure stop word"),
        ("the driver", "CLEANED", "Stop word + meaningful word"),
        ("the driver of the car", "CLEANED", "Multiple stop words"),

        # Valid queries - should pass
        ("driver", "PASS", "Single meaningful word"),
        ("John Doe", "PASS", "Person name"),
        ("191-D-12345", "PASS", "VRN (Vehicle Registration Number)"),

        # Acronyms - should trigger AI enhancement
        ("VRN", "AI_ENHANCED", "Acronym - should expand"),
        ("NCT", "AI_ENHANCED", "Acronym - should expand"),
        ("CVRT", "AI_ENHANCED", "Acronym - should expand"),

        # Mixed cases
        ("the VRN of vehicle", "AI_ENHANCED", "Stop words + acronym"),
        ("driver license", "PASS", "Two meaningful words"),

        # Edge cases
        ("", "REJECTED", "Empty query"),
        ("a", "REJECTED", "Too short + stop word"),
        ("!!!",  "REJECTED", "Only special characters"),
        ("  ", "REJECTED", "Only whitespace"),
    ]

    results = []
    print("\nRunning tests...\n")

    for query, expected, description in test_cases:
        print(f"TEST: {description}")
        print(f"  Query: '{query}'")

        result = preprocessor.preprocess(query)

        # Determine actual behavior
        if not result.is_valid:
            actual = "REJECTED"
            print(f"  Result: REJECTED - {result.rejection_reason}")
        elif result.method == "ai_enhanced":
            actual = "AI_ENHANCED"
            print(f"  Result: AI ENHANCED")
            print(f"  Cleaned: '{result.query}'")
            print(f"  Enhancement: {result.ai_enhancement}")
        elif result.removed_stop_words:
            actual = "CLEANED"
            print(f"  Result: CLEANED (removed stop words)")
            print(f"  Removed: {result.removed_stop_words}")
            print(f"  Cleaned: '{result.query}'")
        else:
            actual = "PASS"
            print(f"  Result: PASS (no changes)")
            print(f"  Query: '{result.query}'")

        # Check if matches expected
        status = "[+] PASS" if actual == expected else f"[-] FAIL (expected {expected})"
        print(f"  Status: {status}")
        print()

        results.append({
            "query": query,
            "description": description,
            "expected": expected,
            "actual": actual,
            "passed": actual == expected,
            "result": result
        })

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {passed/total*100:.1f}%")

    # Show failures
    failures = [r for r in results if not r["passed"]]
    if failures:
        print("\n" + "-" * 80)
        print("FAILURES:")
        print("-" * 80)
        for f in failures:
            print(f"\n[-] {f['description']}")
            print(f"   Query: '{f['query']}'")
            print(f"   Expected: {f['expected']}")
            print(f"   Actual: {f['actual']}")

    print("\n" + "=" * 80)

    # Test specific scenarios
    print("\nSPECIFIC SCENARIO TESTS:")
    print("=" * 80)

    # Scenario 1: User searches for "the" - should be rejected
    print("\nScenario 1: User searches for 'the'")
    result = preprocessor.preprocess("the")
    if not result.is_valid:
        print("[+] CORRECT: Query rejected")
        print(f"   Reason: {result.rejection_reason}")
    else:
        print("[-] WRONG: Query should have been rejected!")

    # Scenario 2: User searches for "the driver" - should remove "the"
    print("\nScenario 2: User searches for 'the driver'")
    result = preprocessor.preprocess("the driver")
    if result.is_valid and result.query == "driver":
        print("[+] CORRECT: Stop word removed")
        print(f"   Original: 'the driver'")
        print(f"   Cleaned: '{result.query}'")
    else:
        print("[-] WRONG: Should have removed 'the'")

    # Scenario 3: User searches for "VRN" - should expand via AI
    print("\nScenario 3: User searches for 'VRN'")
    result = preprocessor.preprocess("VRN")
    if result.method == "ai_enhanced":
        print("[+] CORRECT: AI enhancement triggered")
        print(f"   Original: 'VRN'")
        print(f"   Enhanced: '{result.query}'")
    else:
        print("[!] WARNING: AI enhancement not triggered (might be disabled)")
        print(f"   Query: '{result.query}'")

    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_preprocessing()
