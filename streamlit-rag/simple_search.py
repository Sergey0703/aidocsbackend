#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simple_search.py - Simple Console Search Script
Quick command-line search for your vector database.

Usage:
    python simple_search.py "your search query"
    python simple_search.py "John Nolan" --top-k 10 --threshold 0.3
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv()

# Configure logging - only show our output
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)


async def search(query: str, top_k: int = 20, threshold: float = 0.30, verbose: bool = False):
    """Execute a simple search"""
    try:
        from config.settings import ProductionRAGConfig
        from retrieval.multi_retriever import MultiStrategyRetriever
        from query_processing.entity_extractor import ProductionEntityExtractor
        from query_processing.query_rewriter import ProductionQueryRewriter

        # Initialize system
        if verbose:
            print("\n🔧 Initializing system...")

        config = ProductionRAGConfig()
        retriever = MultiStrategyRetriever(config)

        # Optional: Extract entities
        entity_extractor = ProductionEntityExtractor(config)
        extracted_entity = None

        if verbose:
            print("🔎 Analyzing query...")

        try:
            entity_result = await entity_extractor.extract_entity(query)
            if entity_result and entity_result.entity:
                extracted_entity = entity_result.entity
                if verbose:
                    print(f"✅ Entity detected: '{extracted_entity}' (method: {entity_result.method}, confidence: {entity_result.confidence:.2f})")
        except:
            pass

        # Generate query variants
        query_rewriter = ProductionQueryRewriter(config)
        queries = [query]

        if verbose:
            print("🔄 Generating query variants...")

        try:
            rewrite_result = await query_rewriter.rewrite_query(query, extracted_entity)
            if rewrite_result and rewrite_result.rewrites:
                queries.extend(rewrite_result.rewrites[1:3])
        except:
            pass

        # Perform search
        print(f"\n🔍 Searching for: '{query}'")
        if extracted_entity and extracted_entity != query:
            print(f"🎯 Entity: '{extracted_entity}'")

        print("-" * 80)

        result = await retriever.multi_retrieve(
            queries=queries,
            extracted_entity=extracted_entity
        )

        # Display results
        if not result or not result.results:
            print("❌ No results found\n")
            return

        print(f"\n✅ Found {len(result.results)} results (from {result.total_candidates} candidates)")
        print(f"⏱️  Search time: {result.retrieval_time:.3f}s")
        print(f"🔧 Methods: {', '.join(result.methods_used)}")

        if verbose and result.metadata:
            print(f"📊 Strategy: {result.metadata.get('strategy', 'N/A')}")

        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        for i, res in enumerate(result.results, 1):
            print(f"\n{i}. 📄 {res.filename}")
            print(f"   Score: {res.similarity_score:.4f}", end="")

            if "hybrid_score" in res.metadata:
                print(f" | Hybrid: {res.metadata['hybrid_score']:.4f}", end="")

            print(f"\n   Source: {res.source_method}", end="")

            if "match_type" in res.metadata:
                print(f" | Match: {res.metadata['match_type']}", end="")

            print()

            # Content preview (first 150 chars)
            content_preview = res.content[:150].replace('\n', ' ')
            if len(res.content) > 150:
                content_preview += "..."
            print(f"   Preview: {content_preview}")

            if res.chunk_index:
                print(f"   Chunk: {res.chunk_index}")

        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Simple console search for vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python simple_search.py "John Nolan"
  python simple_search.py "191-D-12345" --top-k 10
  python simple_search.py "insurance documents" --threshold 0.25 --verbose
  python simple_search.py "show me NCT records"
        """
    )

    parser.add_argument(
        "query",
        type=str,
        help="Search query"
    )

    parser.add_argument(
        "-k", "--top-k",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)"
    )

    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.30,
        help="Similarity threshold 0.0-1.0 (default: 0.30)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.query.strip():
        print("❌ Error: Query cannot be empty")
        sys.exit(1)

    if not 0.0 <= args.threshold <= 1.0:
        print("❌ Error: Threshold must be between 0.0 and 1.0")
        sys.exit(1)

    if args.top_k < 1:
        print("❌ Error: top-k must be at least 1")
        sys.exit(1)

    # Run search
    try:
        asyncio.run(search(
            query=args.query,
            top_k=args.top_k,
            threshold=args.threshold,
            verbose=args.verbose
        ))
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
