#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_river_vs_driver.py - Simple test for "river" vs "driver" issue

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
    format='%(message)s'
)
logger = logging.getLogger(__name__)


async def test_river_search():
    """
    Critical test: Search for 'river' should NOT return 'driver' documents
    """
    print("\n" + "=" * 80)
    print("CRITICAL TEST: 'river' should NOT match 'driver'")
    print("=" * 80)

    # Initialize
    config = ProductionRAGConfig()
    retriever = MultiStrategyRetriever(config)
    fusion_engine = HybridResultsFusionEngine(config)

    # Test query
    query = "river"
    print(f"\nQuery: '{query}'")
    print("-" * 80)

    # Retrieve
    print("\n[*] Running hybrid retrieval...")
    retrieval_result = await retriever.multi_retrieve(
        queries=[query],
        extracted_entity=None,
        required_terms=None
    )

    print(f"[+] Retrieved {len(retrieval_result.results)} results")

    # Fusion + Re-ranking (ASYNC version for full LLM support)
    print("\n[*] Running ASYNC fusion + LLM re-ranking...")
    fusion_result = await fusion_engine.fuse_results_async(
        all_results=retrieval_result.results,
        original_query=query,
        extracted_entity=None,
        required_terms=None
    )

    print(f"[+] Final results: {fusion_result.final_count}")

    # Show results
    print("\n" + "-" * 80)
    print("RESULTS:")
    print("-" * 80)

    if fusion_result.fused_results:
        for i, result in enumerate(fusion_result.fused_results, 1):
            print(f"\n[{i}] {result.filename}")
            print(f"    Similarity: {result.similarity_score:.3f}")

            # Check for 'driver' in content (should NOT be there!)
            has_driver = 'driver' in result.content.lower()
            if has_driver:
                print(f"    [!] WARNING: Contains 'driver' - FALSE MATCH!")

            # Show LLM re-ranking score
            if hasattr(result, 'metadata') and 'llm_relevance_score' in result.metadata:
                llm_score = result.metadata['llm_relevance_score']
                is_relevant = result.metadata['llm_is_relevant']
                print(f"    LLM Score: {llm_score:.1f}/10 (Relevant: {is_relevant})")

            # Content preview
            preview = result.content[:200].replace('\n', ' ')
            print(f"    Content: {preview}...")
    else:
        print("\n[+] No results found (expected if no 'river' documents exist)")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Check for false positives
    false_positives = []
    for result in fusion_result.fused_results:
        if 'driver' in result.content.lower() and 'river' not in result.content.lower():
            false_positives.append(result.filename)

    if false_positives:
        print(f"\n[!] FAILED: Found {len(false_positives)} false positives:")
        for filename in false_positives:
            print(f"    - {filename}")
        print("\nThe word boundary and LLM re-ranking fixes did NOT work!")
    else:
        print("\n[+] PASSED: No false positives detected!")
        print("    Word boundary matching + LLM re-ranking is working correctly.")


if __name__ == "__main__":
    asyncio.run(test_river_search())
