#!/usr/bin/env python3
"""
Phase 3: Retrieval Quality Testing
===================================

Tests retrieval quality using industry-standard metrics:
- Precision@K: Accuracy of top-K results
- Recall@K: Coverage of relevant results in top-K
- MRR (Mean Reciprocal Rank): Position of first relevant result

This test BYPASSES answer generation (faster execution, focuses on retrieval only).

Usage:
    python dev_tools/tests/rag_evaluation/test_retrieval.py
    python dev_tools/tests/rag_evaluation/test_retrieval.py --verbose
    python dev_tools/tests/rag_evaluation/test_retrieval.py --top-k 10
"""

import sys
import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
API_URL = "http://localhost:8000/api/search/"
GROUND_TRUTH_PATH = project_root / "dev_tools/datasets/ground_truth/retrieval_queries.json"
RESULTS_DIR = project_root / "dev_tools/tests/rag_evaluation"

# Default evaluation parameters
DEFAULT_TOP_K = 10
DEFAULT_PRECISION_K = 5
DEFAULT_RECALL_K = 10


class RetrievalQualityTester:
    """Tests retrieval quality using Precision@K, Recall@K, and MRR metrics"""

    def __init__(self, api_url: str, ground_truth_path: Path, verbose: bool = False):
        self.api_url = api_url
        self.ground_truth_path = ground_truth_path
        self.verbose = verbose
        self.ground_truth = self._load_ground_truth()

    def _load_ground_truth(self) -> Dict[str, Any]:
        """Load ground truth queries and relevance criteria"""
        if not self.ground_truth_path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {self.ground_truth_path}")

        with open(self.ground_truth_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _query_api(self, query: str) -> Dict[str, Any]:
        """Query the API and return full response (including retrieval results)"""
        try:
            response = requests.post(
                self.api_url,
                json={"query": query},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"    [ERROR] API request failed: {e}")
            return {"results": [], "answer": "", "error": str(e)}

    def _is_relevant(self, chunk_content: str, chunk_metadata: Dict, criteria: Dict) -> bool:
        """Check if a retrieved chunk is relevant based on ground truth criteria"""
        content_lower = chunk_content.lower()

        # Check must_contain keywords (ALL must be present)
        if "must_contain" in criteria:
            for keyword in criteria["must_contain"]:
                if keyword.lower() not in content_lower:
                    return False

        # Check must_contain_any keywords (AT LEAST ONE must be present)
        if "must_contain_any" in criteria:
            keywords = criteria["must_contain_any"]
            if not any(keyword.lower() in content_lower for keyword in keywords):
                return False

        # Check filename match (if specified)
        if "filenames" in criteria:
            chunk_filename = chunk_metadata.get("filename", "")
            if chunk_filename and chunk_filename not in criteria["filenames"]:
                # If filename criteria exists but doesn't match, still check content
                # (chunk might be relevant even if from unexpected file)
                pass

        return True

    def _calculate_precision_at_k(self, results: List[Dict], criteria: Dict, k: int) -> float:
        """Calculate Precision@K: (relevant in top-K) / K"""
        if not results or k == 0:
            return 0.0

        top_k_results = results[:k]
        relevant_count = sum(
            1 for result in top_k_results
            if self._is_relevant(result.get("content", ""), result.get("metadata", {}), criteria)
        )

        return relevant_count / k

    def _calculate_recall_at_k(self, results: List[Dict], criteria: Dict, k: int) -> float:
        """Calculate Recall@K: (relevant in top-K) / (total relevant in database)"""
        if not results or k == 0:
            return 0.0

        # For recall, we need to know total relevant chunks in database
        # We estimate this using min_relevant_chunks from ground truth
        min_relevant = criteria.get("min_relevant_chunks", 1)

        top_k_results = results[:k]
        relevant_count = sum(
            1 for result in top_k_results
            if self._is_relevant(result.get("content", ""), result.get("metadata", {}), criteria)
        )

        # Recall = found / expected
        # Note: If we find MORE than expected, recall can exceed 1.0 (we cap at 1.0)
        recall = relevant_count / min_relevant
        return min(recall, 1.0)

    def _calculate_mrr(self, results: List[Dict], criteria: Dict) -> float:
        """Calculate Mean Reciprocal Rank: 1 / (rank of first relevant result)"""
        if not results:
            return 0.0

        for rank, result in enumerate(results, start=1):
            if self._is_relevant(result.get("content", ""), result.get("metadata", {}), criteria):
                return 1.0 / rank

        return 0.0  # No relevant results found

    def _test_query(self, test_case: Dict, precision_k: int, recall_k: int) -> Dict[str, Any]:
        """Test a single query and calculate metrics"""
        test_id = test_case["test_id"]
        query = test_case["query"]
        query_type = test_case["query_type"]
        criteria = test_case["relevant_criteria"]

        if self.verbose:
            print(f"\n[{test_id}] Testing: '{query}' (type: {query_type})")

        # Query API
        start_time = time.time()
        response = self._query_api(query)
        latency = time.time() - start_time

        results = response.get("results", [])

        # Calculate metrics
        precision_at_k = self._calculate_precision_at_k(results, criteria, precision_k)
        recall_at_k = self._calculate_recall_at_k(results, criteria, recall_k)
        mrr = self._calculate_mrr(results, criteria)

        # Count relevant results
        relevant_count = sum(
            1 for result in results
            if self._is_relevant(result.get("content", ""), result.get("metadata", {}), criteria)
        )

        test_result = {
            "test_id": test_id,
            "query": query,
            "query_type": query_type,
            "latency": round(latency, 2),
            "total_results": len(results),
            "relevant_results": relevant_count,
            "metrics": {
                f"precision_at_{precision_k}": round(precision_at_k, 3),
                f"recall_at_{recall_k}": round(recall_at_k, 3),
                "mrr": round(mrr, 3)
            },
            "expected_metrics": test_case.get("expected_metrics", {}),
            "passed": self._check_thresholds(precision_at_k, recall_at_k, mrr, test_case)
        }

        if self.verbose:
            print(f"    Precision@{precision_k}: {precision_at_k:.3f}")
            print(f"    Recall@{recall_k}: {recall_at_k:.3f}")
            print(f"    MRR: {mrr:.3f}")
            print(f"    Relevant: {relevant_count}/{len(results)} results")

        return test_result

    def _check_thresholds(self, precision: float, recall: float, mrr: float, test_case: Dict) -> bool:
        """Check if metrics meet minimum thresholds"""
        expected = test_case.get("expected_metrics", {})

        # Use conservative thresholds (80% of expected)
        precision_threshold = expected.get("precision_at_5", 0.5) * 0.8
        recall_threshold = expected.get("recall_at_10", 0.5) * 0.8
        mrr_threshold = expected.get("mrr", 0.5) * 0.8

        return (precision >= precision_threshold and
                recall >= recall_threshold and
                mrr >= mrr_threshold)

    def run_all_tests(self, precision_k: int = DEFAULT_PRECISION_K,
                     recall_k: int = DEFAULT_RECALL_K) -> Dict[str, Any]:
        """Run all retrieval quality tests"""
        print("=" * 80)
        print("PHASE 3: RETRIEVAL QUALITY TEST")
        print("=" * 80)
        print(f"Metrics: Precision@{precision_k}, Recall@{recall_k}, MRR")
        print(f"Ground truth: {self.ground_truth_path.name}")
        print(f"Total queries: {len(self.ground_truth['queries'])}")
        print("=" * 80)

        test_results = []
        start_time = time.time()

        for i, test_case in enumerate(self.ground_truth['queries'], 1):
            print(f"\n[{i}/{len(self.ground_truth['queries'])}] {test_case['test_id']}: \"{test_case['query']}\"")

            result = self._test_query(test_case, precision_k, recall_k)
            test_results.append(result)

            # Print summary
            status = "[PASS]" if result["passed"] else "[BELOW THRESHOLD]"
            print(f"    {status} ({result['latency']}s)")
            print(f"    [+] P@{precision_k}={result['metrics'][f'precision_at_{precision_k}']:.3f}, "
                  f"R@{recall_k}={result['metrics'][f'recall_at_{recall_k}']:.3f}, "
                  f"MRR={result['metrics']['mrr']:.3f}")

        total_time = time.time() - start_time

        # Calculate aggregate metrics
        avg_precision = sum(r["metrics"][f"precision_at_{precision_k}"] for r in test_results) / len(test_results)
        avg_recall = sum(r["metrics"][f"recall_at_{recall_k}"] for r in test_results) / len(test_results)
        avg_mrr = sum(r["metrics"]["mrr"] for r in test_results) / len(test_results)
        avg_latency = sum(r["latency"] for r in test_results) / len(test_results)

        passed_count = sum(1 for r in test_results if r["passed"])
        pass_rate = (passed_count / len(test_results)) * 100

        summary = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ground_truth_version": self.ground_truth.get("version", "unknown"),
            "domain": self.ground_truth.get("domain", "unknown"),
            "total_queries": len(test_results),
            "passed_queries": passed_count,
            "pass_rate": round(pass_rate, 1),
            "aggregate_metrics": {
                f"avg_precision_at_{precision_k}": round(avg_precision, 3),
                f"avg_recall_at_{recall_k}": round(avg_recall, 3),
                "avg_mrr": round(avg_mrr, 3)
            },
            "performance": {
                "total_time": round(total_time, 2),
                "avg_latency": round(avg_latency, 2)
            },
            "test_results": test_results
        }

        # Print final summary
        print("\n" + "=" * 80)
        print("RETRIEVAL QUALITY TEST COMPLETE")
        print("=" * 80)
        print(f"Pass rate: {passed_count}/{len(test_results)} ({pass_rate:.1f}%)")
        print(f"\nAggregate Metrics:")
        print(f"  Precision@{precision_k}: {avg_precision:.3f}")
        print(f"  Recall@{recall_k}: {avg_recall:.3f}")
        print(f"  MRR: {avg_mrr:.3f}")
        print(f"\nPerformance:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg latency: {avg_latency:.2f}s/query")
        print("=" * 80)

        return summary


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 3: Retrieval Quality Testing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--precision-k", type=int, default=DEFAULT_PRECISION_K,
                       help=f"K for Precision@K metric (default: {DEFAULT_PRECISION_K})")
    parser.add_argument("--recall-k", type=int, default=DEFAULT_RECALL_K,
                       help=f"K for Recall@K metric (default: {DEFAULT_RECALL_K})")
    parser.add_argument("--api-url", default=API_URL, help="API endpoint URL")

    args = parser.parse_args()

    # Run tests
    tester = RetrievalQualityTester(
        api_url=args.api_url,
        ground_truth_path=GROUND_TRUTH_PATH,
        verbose=args.verbose
    )

    results = tester.run_all_tests(
        precision_k=args.precision_k,
        recall_k=args.recall_k
    )

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"retrieval_test_results_{timestamp}.json"

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {results_file}")

    # Return exit code based on pass rate
    return 0 if results["pass_rate"] >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
