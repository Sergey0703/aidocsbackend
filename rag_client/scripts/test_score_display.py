#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_score_display.py - Test that scores are displayed correctly to users

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


async def test_vrn_search():
    """
    Test VRN search and verify score display is accurate
    """
    print("\n" + "=" * 80)
    print("TEST: VRN search score display")
    print("=" * 80)

    # Initialize
    config = ProductionRAGConfig()
    retriever = MultiStrategyRetriever(config)
    fusion_engine = HybridResultsFusionEngine(config)

    # Test query (VRN format)
    query = "231-D-54321"
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

    # Fusion + Re-ranking
    print("\n[*] Running ASYNC fusion + LLM re-ranking...")
    fusion_result = await fusion_engine.fuse_results_async(
        all_results=retrieval_result.results,
        original_query=query,
        extracted_entity=None,
        required_terms=None
    )

    print(f"[+] Final results: {fusion_result.final_count}")

    # Show results with score analysis
    print("\n" + "-" * 80)
    print("SCORE ANALYSIS:")
    print("-" * 80)

    if fusion_result.fused_results:
        for i, result in enumerate(fusion_result.fused_results, 1):
            print(f"\n[{i}] {result.filename}")
            print(f"    Base similarity_score: {result.similarity_score:.3f} ({result.similarity_score * 100:.1f}%)")

            # Check for LLM score
            if hasattr(result, 'metadata') and 'llm_relevance_score' in result.metadata:
                llm_score = result.metadata['llm_relevance_score']
                is_relevant = result.metadata['llm_is_relevant']
                print(f"    LLM relevance score: {llm_score:.1f}/10 ({llm_score * 10:.1f}%)")
                print(f"    LLM says relevant: {is_relevant}")

                # Suggested display score
                display_score = llm_score / 10.0
                print(f"    -> DISPLAY TO USER: {display_score * 100:.1f}%")
            else:
                print("    No LLM score available")
                print(f"    -> DISPLAY TO USER: {result.similarity_score * 100:.1f}%")

            # Check match type
            if hasattr(result, 'metadata'):
                match_type = result.metadata.get('match_type', 'unknown')
                print(f"    Match type: {match_type}")
    else:
        print("\n[!] No results found")

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)

    if fusion_result.fused_results:
        result = fusion_result.fused_results[0]
        base_score = result.similarity_score

        if hasattr(result, 'metadata') and 'llm_relevance_score' in result.metadata:
            llm_score = result.metadata['llm_relevance_score']
            display_score = llm_score / 10.0

            print(f"\nOLD APPROACH (misleading):")
            print(f"  Show base score: {base_score * 100:.1f}% (looks poor!)")

            print(f"\nNEW APPROACH (accurate):")
            print(f"  Show LLM score: {display_score * 100:.1f}% (reflects true relevance!)")

            if display_score > base_score:
                improvement = (display_score - base_score) * 100
                print(f"\n[+] Improvement: +{improvement:.1f} percentage points")
                print(f"    User sees more accurate relevance score!")
        else:
            print(f"\n[!] No LLM score available - showing base score: {base_score * 100:.1f}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_vrn_search())
