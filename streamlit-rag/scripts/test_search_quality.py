#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_search_quality.py - Test search quality with edge cases like "river" vs "driver"

import sys
import os
import asyncio
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.settings import ProductionRAGConfig
from retrieval.multi_retriever import MultiStrategyRetriever
from retrieval.results_fusion import HybridResultsFusionEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_search(query: str, description: str = ""):
    """Test a single search query"""
    print("\n" + "=" * 80)
    print(f"TEST: {description or query}")
    print("=" * 80)
    print(f"Query: '{query}'")
    print("-" * 80)

    try:
        # Initialize components
        config = ProductionRAGConfig()
        retriever = MultiStrategyRetriever(config)
        fusion_engine = HybridResultsFusionEngine(config)

        # Perform multi-strategy retrieval
        print("\n[*] Running multi-strategy retrieval...")
        retrieval_result = await retriever.multi_retrieve(
            queries=[query],
            extracted_entity=None,
            required_terms=None
        )

        print(f"[+] Retrieved {len(retrieval_result.results)} results from {len(retrieval_result.methods_used)} methods")
        print(f"    Methods: {', '.join(retrieval_result.methods_used)}")

        # Perform results fusion (ASYNC version for full LLM re-ranking)
        print("\n[*] Running ASYNC hybrid results fusion + LLM re-ranking...")
        fusion_result = await fusion_engine.fuse_results_async(
            all_results=retrieval_result.results,
            original_query=query,
            extracted_entity=None,
            required_terms=None
        )

        print(f"[+] Fusion complete: {fusion_result.original_count} -> {fusion_result.final_count} results")
        print(f"    Method: {fusion_result.fusion_method}")
        print(f"    Time: {fusion_result.fusion_time:.2f}s")

        # Display results
        print("\n" + "-" * 80)
        print("RESULTS:")
        print("-" * 80)

        if fusion_result.fused_results:
            for i, result in enumerate(fusion_result.fused_results, 1):
                print(f"\n[{i}] {result.filename}")
                print(f"    Source: {result.source_method}")
                print(f"    Similarity: {result.similarity_score:.3f}")

                # Show LLM re-ranking metadata if present
                if hasattr(result, 'metadata') and result.metadata:
                    if 'llm_relevance_score' in result.metadata:
                        llm_score = result.metadata.get('llm_relevance_score', 'N/A')
                        is_relevant = result.metadata.get('llm_is_relevant', 'N/A')
                        print(f"    LLM Relevance: {llm_score:.1f}/10 (Relevant: {is_relevant})")

                # Show content preview
                content_preview = result.content[:150].replace('\n', ' ')
                print(f"    Content: {content_preview}...")
        else:
            print("\n[!] No results found")

        print("\n" + "=" * 80)

        return fusion_result

    except Exception as e:
        logger.error(f"[!] Search failed: {e}", exc_info=True)
        return None


async def main():
    """Run test suite"""
    print("\n")
    print("=" * 80)
    print("SEARCH QUALITY TEST SUITE")
    print("=" * 80)
    print("\nTesting LLM re-ranking with Gemini API")
    print("Expected: 'river' should NOT match 'driver' documents\n")

    # Test cases
    test_cases = [
        ("river", "False match test: 'river' should NOT find 'driver' documents"),
        ("driver", "True match test: 'driver' should find driver-related documents"),
        ("John", "Partial name test: Should find 'John' but not 'Johnson' (unless same person)"),
        ("CVRT", "Acronym test: Should find CVRT documents"),
        ("191-D-12345", "VRN test: Should find specific vehicle registration"),
    ]

    results = []
    for query, description in test_cases:
        result = await test_search(query, description)
        results.append((query, description, result))

        # Wait between tests to avoid rate limiting
        await asyncio.sleep(2)

    # Summary
    print("\n\n")
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for query, description, result in results:
        if result:
            print(f"\n{description}")
            print(f"  Query: '{query}'")
            print(f"  Results: {result.final_count}")
            print(f"  Method: {result.fusion_method}")

            # Check for LLM re-ranking
            if result.fused_results:
                llm_reranked = any(
                    hasattr(r, 'metadata') and 'llm_relevance_score' in r.metadata
                    for r in result.fused_results
                )
                print(f"  LLM Re-ranking: {'YES' if llm_reranked else 'NO'}")
        else:
            print(f"\n{description}")
            print(f"  Query: '{query}'")
            print(f"  Results: FAILED")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
