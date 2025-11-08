#!/usr/bin/env python3
"""
Smoke Test for RAG System

Quick sanity check (< 1 minute) that runs 5 critical test cases:
1. Exact VRN lookup (vrn_001)
2. Aggregation query (agg_001)
3. Entity search (entity_001)
4. Semantic query (semantic_001)
5. Negative test (neg_001)

Based on ground truth from: dev_tools/datasets/ground_truth/vehicle_queries.json

Usage:
    python dev_tools/tests/rag_evaluation/smoke_test.py

Prerequisites:
    - API server running on http://localhost:8000
    - Database populated with test documents
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

API_BASE_URL = "http://localhost:8000"
SEARCH_ENDPOINT = f"{API_BASE_URL}/api/search/"
GROUND_TRUTH_PATH = "dev_tools/datasets/ground_truth/vehicle_queries.json"

# Test cases to run (IDs from ground truth)
SMOKE_TEST_CASES = [
    "vrn_001",       # Exact VRN lookup
    "agg_001",       # Aggregation (how many cars)
    "entity_001",    # Entity search (VCR documents)
    "semantic_001",  # Semantic search (vehicle info)
    "neg_001"        # Negative test (out of domain)
]

# ============================================================================
# Helper Functions
# ============================================================================

def load_ground_truth():
    """Load ground truth test cases from JSON file."""
    try:
        with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['test_cases']
    except FileNotFoundError:
        print(f"[ERROR] Ground truth file not found: {GROUND_TRUTH_PATH}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load ground truth: {e}")
        return []

def check_api_health():
    """Check if API server is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def query_api(query: str, timeout: int = 30):
    """
    Send search query to API.

    Args:
        query: Search query string
        timeout: Request timeout in seconds

    Returns:
        tuple: (success: bool, response_data: dict, latency: float)
    """
    start_time = time.time()

    try:
        response = requests.post(
            SEARCH_ENDPOINT,
            json={"query": query},
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )

        latency = time.time() - start_time

        if response.status_code == 200:
            return True, response.json(), latency
        else:
            return False, {"error": response.text, "status_code": response.status_code}, latency

    except requests.Timeout:
        latency = time.time() - start_time
        return False, {"error": "Request timeout"}, latency
    except Exception as e:
        latency = time.time() - start_time
        return False, {"error": str(e)}, latency

def check_keywords_in_answer(answer: str, expected_keywords: list) -> tuple:
    """
    Check if expected keywords are present in answer.

    Returns:
        tuple: (all_found: bool, found_keywords: list, missing_keywords: list)
    """
    if not answer:
        return False, [], expected_keywords

    answer_lower = answer.lower()
    found = []
    missing = []

    for keyword in expected_keywords:
        if keyword.lower() in answer_lower:
            found.append(keyword)
        else:
            missing.append(keyword)

    all_found = len(missing) == 0
    return all_found, found, missing

def evaluate_test_case(test_case: dict, response_data: dict, latency: float) -> dict:
    """
    Evaluate test case results against expected outcomes.

    Returns:
        dict: Evaluation results with pass/fail status
    """
    result = {
        "test_id": test_case["id"],
        "query": test_case["query"],
        "query_type": test_case["query_type"],
        "latency": latency,
        "passed": False,
        "checks": []
    }

    # Check if response has answer
    if "answer" not in response_data:
        result["checks"].append({
            "name": "Response structure",
            "passed": False,
            "message": "No 'answer' field in response"
        })
        return result

    answer = response_data["answer"]

    # For negative tests (should reject)
    if test_case.get("should_reject"):
        expected_keywords = test_case.get("expected_answer_contains", [])
        all_found, found, missing = check_keywords_in_answer(answer, expected_keywords)

        result["checks"].append({
            "name": "Rejection handling",
            "passed": all_found,
            "message": f"Found rejection keywords: {found}" if all_found else f"Missing: {missing}",
            "found_keywords": found,
            "missing_keywords": missing
        })
        result["passed"] = all_found
        return result

    # For normal tests - check expected keywords
    expected_keywords = test_case.get("expected_answer_contains", [])
    if expected_keywords:
        all_found, found, missing = check_keywords_in_answer(answer, expected_keywords)

        result["checks"].append({
            "name": "Expected keywords",
            "passed": all_found,
            "message": f"Found: {found}" if all_found else f"Missing: {missing}",
            "found_keywords": found,
            "missing_keywords": missing
        })
        result["passed"] = all_found

    # Check for "may contain" keywords (optional)
    may_contain = test_case.get("expected_answer_may_contain", [])
    if may_contain:
        any_found, found, missing = check_keywords_in_answer(answer, may_contain)

        result["checks"].append({
            "name": "Optional keywords",
            "passed": len(found) > 0,
            "message": f"Found: {found}" if found else "None found",
            "found_keywords": found
        })

    # Check retrieval count (if specified)
    if "results" in response_data:
        result_count = len(response_data["results"])
        result["checks"].append({
            "name": "Results retrieved",
            "passed": result_count > 0,
            "message": f"{result_count} results"
        })

    return result

# ============================================================================
# Main Smoke Test
# ============================================================================

def run_smoke_test():
    """Run smoke test suite."""

    print("\n" + "=" * 80)
    print("SMOKE TEST (Quick Sanity Check)")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {SEARCH_ENDPOINT}")
    print()

    # ========================================================================
    # Pre-flight checks
    # ========================================================================

    print("[*] Pre-flight checks...")

    # Check API is running
    if not check_api_health():
        print("[ERROR] API server is not running!")
        print(f"       Please start the server: python run_api.py")
        print(f"       Expected URL: {API_BASE_URL}")
        return

    print("[+] API server is running")

    # Load ground truth
    test_cases = load_ground_truth()
    if not test_cases:
        print("[ERROR] No test cases loaded from ground truth")
        return

    print(f"[+] Loaded {len(test_cases)} test cases from ground truth")

    # Filter smoke test cases
    smoke_tests = [tc for tc in test_cases if tc["id"] in SMOKE_TEST_CASES]

    if len(smoke_tests) != len(SMOKE_TEST_CASES):
        found_ids = [tc["id"] for tc in smoke_tests]
        missing = set(SMOKE_TEST_CASES) - set(found_ids)
        print(f"[WARNING] Some smoke test cases not found: {missing}")

    print(f"[+] Running {len(smoke_tests)} smoke tests")
    print()

    # ========================================================================
    # Run tests
    # ========================================================================

    results = []
    total_time = 0

    for idx, test_case in enumerate(smoke_tests, 1):
        test_id = test_case["id"]
        query = test_case["query"]

        print(f"[{idx}/{len(smoke_tests)}] Testing {test_id}: \"{query}\"")

        # Execute query
        success, response_data, latency = query_api(query)
        total_time += latency

        if not success:
            print(f"    [FAIL] API Error: {response_data.get('error', 'Unknown')} ({latency:.2f}s)")
            results.append({
                "test_id": test_id,
                "query": query,
                "passed": False,
                "latency": latency,
                "error": response_data.get('error')
            })
            print()
            continue

        # Evaluate response
        evaluation = evaluate_test_case(test_case, response_data, latency)
        results.append(evaluation)

        # Print result
        status = "[PASS]" if evaluation["passed"] else "[FAIL]"
        print(f"    {status} ({latency:.2f}s)")

        # Print check details
        for check in evaluation["checks"]:
            check_status = "[+]" if check["passed"] else "[-]"
            print(f"      {check_status} {check['name']}: {check['message']}")

        print()

    # ========================================================================
    # Summary
    # ========================================================================

    print("=" * 80)
    print("SMOKE TEST RESULTS")
    print("=" * 80)

    passed_count = sum(1 for r in results if r.get("passed", False))
    total_count = len(results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"Tests Passed:  {passed_count}/{total_count} ({pass_rate:.1f}%)")
    print(f"Total Time:    {total_time:.2f}s")
    print(f"Avg Latency:   {total_time/total_count:.2f}s" if total_count > 0 else "N/A")
    print()

    # Breakdown by query type
    print("By Query Type:")
    type_stats = {}
    for result in results:
        qtype = result.get("query_type", "unknown")
        if qtype not in type_stats:
            type_stats[qtype] = {"passed": 0, "total": 0}
        type_stats[qtype]["total"] += 1
        if result.get("passed", False):
            type_stats[qtype]["passed"] += 1

    for qtype, stats in type_stats.items():
        rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "[+]" if stats["passed"] == stats["total"] else "[-]"
        print(f"  {status} {qtype}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

    print()

    # Failed tests details
    failed_tests = [r for r in results if not r.get("passed", False)]
    if failed_tests:
        print("=" * 80)
        print("FAILED TESTS DETAILS")
        print("=" * 80)

        for result in failed_tests:
            print(f"\n[FAIL] {result['test_id']}: \"{result['query']}\"")

            if "error" in result:
                print(f"  Error: {result['error']}")

            for check in result.get("checks", []):
                if not check["passed"]:
                    print(f"  [-] {check['name']}: {check['message']}")
                    if "missing_keywords" in check:
                        print(f"      Missing: {check['missing_keywords']}")

        print()

    # ========================================================================
    # Final verdict
    # ========================================================================

    print("=" * 80)
    if pass_rate == 100:
        print("[SUCCESS] ALL TESTS PASSED - System is working correctly!")
    elif pass_rate >= 80:
        print("[WARNING] MOST TESTS PASSED - Some issues detected")
    else:
        print("[FAILURE] MULTIPLE FAILURES - System needs attention")
    print("=" * 80)
    print()

    # Save results to file
    results_file = f"dev_tools/tests/rag_evaluation/smoke_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_count,
                "passed": passed_count,
                "pass_rate": pass_rate,
                "total_time": total_time,
                "results": results
            }, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {results_file}")
    except Exception as e:
        print(f"[WARNING] Could not save results: {e}")

    print()

if __name__ == "__main__":
    run_smoke_test()
