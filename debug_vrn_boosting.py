#!/usr/bin/env python3
"""
Debug VRN Boosting
==================

This script tests VRN pattern detection and boosting logic directly.
Tests the exact query "231-D-54321" to see if boosting is applied.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_vrn_detection():
    """Test VRN pattern detection methods"""
    print("=" * 80)
    print("VRN PATTERN DETECTION TEST")
    print("=" * 80)

    # Import after path setup
    from rag_client.retrieval.multi_retriever import MultiStrategyRetriever
    from rag_client.config.settings import config

    retriever = MultiStrategyRetriever(config)

    test_cases = [
        ("231-D-54321", "exact VRN"),
        ("141-D-98765", "exact VRN"),
        ("231-D", "partial VRN"),
        ("141-D", "partial VRN"),
        ("all vehicles", "aggregation query"),
        ("how many cars", "aggregation query"),
        ("Volvo FH460", "not VRN"),
        ("insurance certificate", "not VRN"),
    ]

    print("\n1. Testing VRN Pattern Detection:")
    print("-" * 80)
    for query, expected_type in test_cases:
        is_vrn = retriever._is_vrn_pattern(query)
        is_partial = retriever._is_partial_vrn(query)
        is_agg = retriever._is_aggregation_query(query)

        print(f"\nQuery: '{query}' (expected: {expected_type})")
        print(f"  _is_vrn_pattern():      {is_vrn}")
        print(f"  _is_partial_vrn():      {is_partial}")
        print(f"  _is_aggregation_query(): {is_agg}")

        # Validate
        if expected_type == "exact VRN" and not is_vrn:
            print(f"  [ERROR] Should detect as exact VRN!")
        elif expected_type == "partial VRN" and not is_partial:
            print(f"  [ERROR] Should detect as partial VRN!")
        elif expected_type == "aggregation query" and not is_agg:
            print(f"  [ERROR] Should detect as aggregation query!")
        else:
            print(f"  [OK] Detection correct")

    print("\n2. Testing Aggregation Query Rewriting:")
    print("-" * 80)
    agg_queries = [
        "all vehicles",
        "how many cars",
        "list all VRNs",
        "show me all cars",
    ]

    for query in agg_queries:
        rewritten = retriever._rewrite_aggregation_query(query)
        print(f"\nOriginal:  '{query}'")
        print(f"Rewritten: '{rewritten}'")
        if rewritten == query:
            print(f"  [WARN] Query not rewritten!")
        else:
            print(f"  [OK] Query rewritten successfully")


def test_vrn_retrieval():
    """Test actual retrieval for VRN query with detailed logging"""
    print("\n" + "=" * 80)
    print("VRN RETRIEVAL TEST - Query: '231-D-54321'")
    print("=" * 80)

    import requests
    import json

    query = "231-D-54321"
    api_url = "http://localhost:8000/api/search/"

    print(f"\nQuerying API: {api_url}")
    print(f"Query: '{query}'")

    try:
        response = requests.post(
            api_url,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        answer = data.get("answer", "")

        print(f"\n[OK] API Response received")
        print(f"Total results: {len(results)}")
        print(f"Answer preview: {answer[:200]}...")

        print("\n" + "-" * 80)
        print("DETAILED RESULTS ANALYSIS:")
        print("-" * 80)

        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0)

            print(f"\n[Result {i}]")
            print(f"  Score: {score:.4f}")
            print(f"  Filename: {metadata.get('filename', 'N/A')}")
            print(f"  Source method: {metadata.get('source_method', 'N/A')}")
            print(f"  Match type: {metadata.get('match_type', 'N/A')}")
            print(f"  Content preview: {content[:150]}...")

            # Check if VRN appears in content
            if "231-D-54321" in content or "231-d-54321" in content.lower():
                print(f"  [OK] VRN '231-D-54321' found in content")
            else:
                print(f"  [WARN] VRN '231-D-54321' NOT found in content")

        # Analyze scoring
        print("\n" + "-" * 80)
        print("SCORING ANALYSIS:")
        print("-" * 80)

        if results:
            top_score = results[0].get("score", 0)
            has_vrn = "231-D-54321" in results[0].get("content", "").upper()
            source_method = results[0].get("metadata", {}).get("source_method", "")

            print(f"Top result score: {top_score:.4f}")
            print(f"Top result has VRN: {has_vrn}")
            print(f"Top result source: {source_method}")

            # Check if boosting was applied
            if has_vrn and top_score > 1.0:
                print(f"\n[OK] BOOSTING LIKELY APPLIED (score > 1.0)")
            elif has_vrn and top_score <= 1.0:
                print(f"\n[WARN] BOOSTING MAY NOT BE APPLIED (score <= 1.0)")
                print(f"   Expected: score > 3.0 for exact VRN match")
            elif not has_vrn:
                print(f"\n[ERROR] TOP RESULT DOESN'T CONTAIN VRN")
                print(f"   This indicates boosting is not working correctly")

        # Check relevance
        print("\n" + "-" * 80)
        print("RELEVANCE CHECK:")
        print("-" * 80)

        relevant_count = sum(
            1 for r in results
            if "231-D-54321" in r.get("content", "").upper()
        )

        print(f"Results containing '231-D-54321': {relevant_count}/{len(results)}")

        if len(results) >= 5:
            top5_relevant = sum(
                1 for r in results[:5]
                if "231-D-54321" in r.get("content", "").upper()
            )
            precision_at_5 = top5_relevant / 5
            print(f"Precision@5: {precision_at_5:.1%} ({top5_relevant}/5)")
        else:
            precision_at_k = relevant_count / len(results) if results else 0
            print(f"Precision@{len(results)}: {precision_at_k:.1%} ({relevant_count}/{len(results)})")

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] API request failed: {e}")
        print(f"   Make sure API server is running: python run_api.py")
        return
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


def test_database_chunks():
    """Check how many chunks exist for VRN '231-D-54321' in database"""
    print("\n" + "=" * 80)
    print("DATABASE CHUNKS CHECK - VRN: '231-D-54321'")
    print("=" * 80)

    try:
        import os
        from sqlalchemy import create_engine, text
        from dotenv import load_dotenv

        load_dotenv("rag_client/.env")

        connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
        if not connection_string:
            print("[ERROR] SUPABASE_CONNECTION_STRING not found in .env")
            return

        engine = create_engine(connection_string)

        with engine.connect() as conn:
            # Check total chunks
            result = conn.execute(text("SELECT COUNT(*) FROM vecs.documents"))
            total_chunks = result.scalar()
            print(f"\nTotal chunks in database: {total_chunks}")

            # Search for chunks containing VRN
            query = text("""
                SELECT
                    id,
                    metadata->>'filename' as filename,
                    LEFT(content, 100) as content_preview
                FROM vecs.documents
                WHERE content ILIKE :vrn
                ORDER BY metadata->>'filename'
            """)

            result = conn.execute(query, {"vrn": "%231-D-54321%"})
            chunks = result.fetchall()

            print(f"\nChunks containing '231-D-54321': {len(chunks)}")

            if chunks:
                print("\nChunk details:")
                for i, chunk in enumerate(chunks, 1):
                    print(f"  [{i}] {chunk.filename}")
                    print(f"      Content: {chunk.content_preview}...")
            else:
                print("\n[WARN] No chunks found containing '231-D-54321'")
                print("   This explains why precision is low!")

                # Check if VRN exists in any form
                query_fuzzy = text("""
                    SELECT
                        id,
                        metadata->>'filename' as filename,
                        LEFT(content, 100) as content_preview
                    FROM vecs.documents
                    WHERE content ILIKE '%231%D%54321%'
                    ORDER BY metadata->>'filename'
                    LIMIT 5
                """)

                result = conn.execute(query_fuzzy)
                fuzzy_chunks = result.fetchall()

                if fuzzy_chunks:
                    print("\n   Fuzzy search found similar patterns:")
                    for chunk in fuzzy_chunks:
                        print(f"     - {chunk.filename}: {chunk.content_preview}...")

    except Exception as e:
        print(f"\n[ERROR] Database check failed: {e}")
        print(f"   Make sure .env file exists and connection string is correct")


def main():
    """Run all debug tests"""
    print("\n" + "=" * 80)
    print("VRN BOOSTING DEBUG SUITE")
    print("=" * 80)

    # Test 1: Pattern detection
    print("\n>>> TEST 1: VRN Pattern Detection")
    try:
        test_vrn_detection()
    except Exception as e:
        print(f"[ERROR] Test 1 failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Database chunks
    print("\n>>> TEST 2: Database Chunks Check")
    try:
        test_database_chunks()
    except Exception as e:
        print(f"[ERROR] Test 2 failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Actual retrieval
    print("\n>>> TEST 3: API Retrieval Test")
    try:
        test_vrn_retrieval()
    except Exception as e:
        print(f"[ERROR] Test 3 failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("DEBUG SUITE COMPLETE")
    print("=" * 80)
    print("\nNext steps based on results:")
    print("1. If pattern detection fails → Fix regex patterns")
    print("2. If database has no chunks → Need to index more documents")
    print("3. If boosting not applied → Check _calculate_hybrid_score() logic")
    print("4. If API returns wrong results → Check hybrid fusion logic")


if __name__ == "__main__":
    main()
