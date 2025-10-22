#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_driver_query.py - Test that "driver" query works correctly

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


async def test_driver_search():
    """
    Test: Search for 'driver' should find driver-related documents
    AND LLM should confirm relevance (not filter them out)
    """
    print("\n" + "=" * 80)
    print("TEST: 'driver' should find relevant driver documents")
    print("=" * 80)

    # Initialize
    config = ProductionRAGConfig()
    retriever = MultiStrategyRetriever(config)
    fusion_engine = HybridResultsFusionEngine(config)

    # Test query
    query = "driver"
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

    # Show results
    print("\n" + "-" * 80)
    print("RESULTS:")
    print("-" * 80)

    if fusion_result.fused_results:
        for i, result in enumerate(fusion_result.fused_results, 1):
            print(f"\n[{i}] {result.filename}")
            print(f"    Similarity: {result.similarity_score:.3f}")

            # Show LLM re-ranking score
            if hasattr(result, 'metadata') and 'llm_relevance_score' in result.metadata:
                llm_score = result.metadata['llm_relevance_score']
                is_relevant = result.metadata['llm_is_relevant']
                print(f"    LLM Score: {llm_score:.1f}/10 (Relevant: {is_relevant})")

            # Content preview
            preview = result.content[:200].replace('\n', ' ')
            print(f"    Content: {preview}...")
    else:
        print("\n[!] No results found - UNEXPECTED!")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Check results
    if fusion_result.fused_results:
        print(f"\n[+] SUCCESS: Found {fusion_result.final_count} driver-related document(s)")
        print("    LLM re-ranking correctly kept relevant results.")

        # Check LLM scores
        for result in fusion_result.fused_results:
            if hasattr(result, 'metadata') and 'llm_relevance_score' in result.metadata:
                score = result.metadata['llm_relevance_score']
                if score >= 7.0:
                    print(f"    [+] {result.filename}: LLM score {score:.1f}/10 (HIGH RELEVANCE)")
                else:
                    print(f"    [!] {result.filename}: LLM score {score:.1f}/10 (LOW - should not be here!)")
    else:
        print(f"\n[!] FAILED: No results found for 'driver' query")
        print("    This might indicate over-aggressive filtering.")


if __name__ == "__main__":
    asyncio.run(test_driver_search())
