#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
console_search.py - Interactive Console Search for Vector Database
A powerful console interface for searching your RAG vector database with hybrid search.
"""

import os
import sys
import asyncio
import logging
from typing import Optional, List
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Suppress Pydantic warning from llama-index library
import warnings
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    module='pydantic._internal._generate_schema',
    message='.*validate_default.*'
)

# Import configuration and retrieval components
try:
    from config.settings import ProductionRAGConfig
    from retrieval.multi_retriever import MultiStrategyRetriever
    from query_processing.entity_extractor import EntityExtractor
    from query_processing.query_rewriter import QueryRewriter
except ImportError as e:
    logger.error(f"❌ Import error: {e}")
    logger.error("Make sure you're running this script from the client_rag directory")
    sys.exit(1)


class ConsoleSearchApp:
    """Interactive console search application"""

    def __init__(self):
        """Initialize the search application"""
        print("\n" + "="*80)
        print("  VECTOR DATABASE CONSOLE SEARCH")
        print("  RAG System with Hybrid Search (Vector + Database)")
        print("="*80)

        # Initialize configuration
        print("\n🔧 Initializing configuration...")
        try:
            self.config = ProductionRAGConfig()
            print("✅ Configuration loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)

        # Initialize retriever
        print("🔧 Initializing multi-strategy retriever...")
        try:
            self.retriever = MultiStrategyRetriever(self.config)
            print("✅ Retriever initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize retriever: {e}")
            sys.exit(1)

        # Initialize query processors
        print("🔧 Initializing query processors...")
        try:
            self.entity_extractor = EntityExtractor(self.config)
            self.query_rewriter = QueryRewriter(self.config)
            print("✅ Query processors initialized successfully")
        except Exception as e:
            print(f"⚠️ Warning: Query processors may be limited: {e}")
            self.entity_extractor = None
            self.query_rewriter = None

        # Check system health
        print("\n🏥 Running system health check...")
        self._check_health()

    def _check_health(self):
        """Check system health"""
        try:
            health = asyncio.run(self.retriever.health_check())

            if health.get("overall_healthy"):
                print("✅ System health: ALL SYSTEMS OPERATIONAL")
            else:
                print("⚠️ System health: Some issues detected")

            print("\n📊 Retriever status:")
            for name, status in health.get("retrievers", {}).items():
                available = status.get("available", False)
                status_icon = "✅" if available else "❌"
                print(f"   {status_icon} {name}: {'Available' if available else 'Unavailable'}")

            if health.get("hybrid_enabled"):
                print("   🔥 Hybrid search: ENABLED")

        except Exception as e:
            print(f"⚠️ Health check warning: {e}")

    def print_menu(self):
        """Print main menu"""
        print("\n" + "="*80)
        print("SEARCH OPTIONS")
        print("-"*80)
        print("1. Quick Search          - Search with automatic entity extraction")
        print("2. Advanced Search       - Search with custom parameters")
        print("3. File Name Search      - Search by document filename")
        print("4. Show Example Queries  - View example search queries")
        print("5. System Status         - Check system health and configuration")
        print("6. Help                  - Show help and tips")
        print("0. Exit                  - Quit the application")
        print("="*80)

    def print_examples(self):
        """Print example queries"""
        print("\n" + "="*80)
        print("EXAMPLE QUERIES")
        print("-"*80)

        examples = self.config.ui.example_queries if hasattr(self.config, 'ui') else [
            "John Nolan",
            "show me John Nolan certifications",
            "191-D-12345",
            "tell me about vehicle insurance",
            "NCT expiry dates",
        ]

        for i, example in enumerate(examples, 1):
            print(f"   {i}. {example}")

        print("="*80)

    def print_help(self):
        """Print help information"""
        print("\n" + "="*80)
        print("HELP & TIPS")
        print("-"*80)
        print("\n📚 Search Tips:")
        print("   • Use person names for driver-related documents")
        print("   • Use VRN (Vehicle Registration Numbers) for vehicle documents")
        print("   • Use specific terms like 'insurance', 'NCT', 'service' for doc types")
        print("   • The system uses hybrid search (vector + database) automatically")
        print("   • Entity extraction helps find exact matches")
        print("\n🔍 Search Types:")
        print("   • Quick Search: Best for most queries, automatic optimization")
        print("   • Advanced Search: Fine-tune similarity threshold and result count")
        print("   • File Name Search: Direct filename lookup in database")
        print("\n⚙️ How It Works:")
        print("   • Vector Search: Semantic similarity using embeddings")
        print("   • Database Search: Exact phrase and term matching")
        print("   • Hybrid Fusion: Combines both methods intelligently")
        print("   • Entity Extraction: Identifies people, vehicles, dates")
        print("="*80)

    async def quick_search(self, query: str):
        """Perform quick search with automatic optimization"""
        print(f"\n🔍 Searching for: '{query}'")
        print("-"*80)

        # Extract entities
        extracted_entity = None
        if self.entity_extractor:
            print("🔎 Extracting entities...")
            try:
                entity_result = await self.entity_extractor.extract_entities(query)
                if entity_result and entity_result.get("entities"):
                    extracted_entity = entity_result["entities"][0]
                    print(f"✅ Entity detected: '{extracted_entity}'")
            except Exception as e:
                print(f"⚠️ Entity extraction warning: {e}")

        # Generate query variants
        queries = [query]
        if self.query_rewriter:
            print("🔄 Generating query variants...")
            try:
                rewrite_result = await self.query_rewriter.rewrite_query(query)
                if rewrite_result and rewrite_result.get("expanded_queries"):
                    queries.extend(rewrite_result["expanded_queries"][:2])
                    print(f"✅ Generated {len(queries)-1} additional variants")
            except Exception as e:
                print(f"⚠️ Query rewriting warning: {e}")

        # Perform search
        print("🚀 Executing hybrid search...")
        try:
            result = await self.retriever.multi_retrieve(
                queries=queries,
                extracted_entity=extracted_entity
            )

            # Display results
            self._display_results(result)

        except Exception as e:
            print(f"❌ Search failed: {e}")
            logger.exception("Search error details:")

    async def advanced_search(self, query: str, top_k: int, similarity_threshold: float):
        """Perform advanced search with custom parameters"""
        print(f"\n🔍 Advanced search for: '{query}'")
        print(f"   Parameters: top_k={top_k}, threshold={similarity_threshold}")
        print("-"*80)

        # Simple search with custom parameters
        print("🚀 Executing search...")
        try:
            # Get search params
            search_params = self.config.get_dynamic_search_params(query)
            search_params['top_k'] = top_k
            search_params['similarity_threshold'] = similarity_threshold

            result = await self.retriever.multi_retrieve(
                queries=[query]
            )

            # Display results
            self._display_results(result)

        except Exception as e:
            print(f"❌ Search failed: {e}")
            logger.exception("Search error details:")

    async def file_name_search(self, filename: str):
        """Search by filename"""
        print(f"\n📄 Searching for filename: '{filename}'")
        print("-"*80)

        try:
            import psycopg2
            import psycopg2.extras

            conn = psycopg2.connect(self.config.database.connection_string)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Search for filename
            sql = """
            SELECT DISTINCT
                metadata->>'file_name' as file_name,
                metadata->>'file_path' as file_path,
                COUNT(*) as chunk_count,
                MIN(id::text) as first_chunk_id
            FROM vecs.documents
            WHERE LOWER(metadata->>'file_name') LIKE LOWER(%s)
            GROUP BY metadata->>'file_name', metadata->>'file_path'
            ORDER BY metadata->>'file_name'
            LIMIT 20
            """

            search_term = f"%{filename}%"
            cur.execute(sql, (search_term,))
            results = cur.fetchall()

            if results:
                print(f"\n✅ Found {len(results)} matching files:")
                print("-"*80)

                for i, row in enumerate(results, 1):
                    print(f"\n{i}. 📄 {row['file_name']}")
                    print(f"   Path: {row['file_path']}")
                    print(f"   Chunks: {row['chunk_count']}")
                    print(f"   ID: {row['first_chunk_id']}")
            else:
                print("❌ No files found matching that name")

            cur.close()
            conn.close()

        except Exception as e:
            print(f"❌ File search failed: {e}")
            logger.exception("File search error details:")

    def _display_results(self, result):
        """Display search results in a formatted way"""
        print("\n" + "="*80)
        print("SEARCH RESULTS")
        print("="*80)

        if not result or not result.results:
            print("❌ No results found")
            return

        # Summary
        print(f"\n📊 Summary:")
        print(f"   • Total results: {len(result.results)}")
        print(f"   • Total candidates: {result.total_candidates}")
        print(f"   • Methods used: {', '.join(result.methods_used)}")
        print(f"   • Retrieval time: {result.retrieval_time:.3f}s")
        print(f"   • Fusion method: {result.fusion_method}")

        # Search strategy info
        if result.metadata:
            strategy = result.metadata.get("strategy", "unknown")
            print(f"   • Search strategy: {strategy}")

            search_params = result.metadata.get("search_params", {})
            if search_params:
                print(f"   • Similarity threshold: {search_params.get('similarity_threshold', 'N/A')}")
                print(f"   • Top K: {search_params.get('top_k', 'N/A')}")

        # Results
        print(f"\n📄 Results (showing top {min(10, len(result.results))}):")
        print("-"*80)

        for i, res in enumerate(result.results[:10], 1):
            print(f"\n{i}. 📄 {res.filename}")
            print(f"   Score: {res.similarity_score:.4f}")
            print(f"   Source: {res.source_method}")

            # Show hybrid score if available
            if "hybrid_score" in res.metadata:
                print(f"   Hybrid Score: {res.metadata['hybrid_score']:.4f}")

            # Show match type if available
            if "match_type" in res.metadata:
                print(f"   Match Type: {res.metadata['match_type']}")

            # Show content preview
            content_preview = res.content[:200] + "..." if len(res.content) > 200 else res.content
            print(f"   Content: {content_preview}")

            # Show chunk info
            if res.chunk_index:
                print(f"   Chunk: {res.chunk_index}")

        print("\n" + "="*80)

    def run(self):
        """Run the interactive console application"""
        print("\n✅ System ready!")

        while True:
            try:
                self.print_menu()
                choice = input("\nEnter your choice (0-6): ").strip()

                if choice == "0":
                    print("\n👋 Thank you for using Vector Database Console Search!")
                    print("="*80 + "\n")
                    break

                elif choice == "1":
                    # Quick search
                    query = input("\n🔍 Enter search query: ").strip()
                    if query:
                        asyncio.run(self.quick_search(query))
                    else:
                        print("❌ Query cannot be empty")

                elif choice == "2":
                    # Advanced search
                    query = input("\n🔍 Enter search query: ").strip()
                    if not query:
                        print("❌ Query cannot be empty")
                        continue

                    try:
                        top_k = int(input("📊 Enter max results (default 20): ").strip() or "20")
                        threshold = float(input("🎯 Enter similarity threshold (0.0-1.0, default 0.30): ").strip() or "0.30")

                        if not 0.0 <= threshold <= 1.0:
                            print("❌ Threshold must be between 0.0 and 1.0")
                            continue

                        asyncio.run(self.advanced_search(query, top_k, threshold))
                    except ValueError:
                        print("❌ Invalid number format")

                elif choice == "3":
                    # File name search
                    filename = input("\n📄 Enter filename (or part of it): ").strip()
                    if filename:
                        asyncio.run(self.file_name_search(filename))
                    else:
                        print("❌ Filename cannot be empty")

                elif choice == "4":
                    # Show examples
                    self.print_examples()

                elif choice == "5":
                    # System status
                    print("\n🏥 Running system health check...")
                    self._check_health()

                    # Show configuration
                    print("\n⚙️ Configuration:")
                    print(f"   • Database: {self.config.database.table_name}")
                    print(f"   • Embedding Model: {self.config.embedding.model_name}")
                    print(f"   • Embedding Dimension: {self.config.embedding.dimension}")
                    print(f"   • Hybrid Search: {'Enabled' if self.config.search.enable_hybrid_search else 'Disabled'}")
                    print(f"   • Vector Search: {'Enabled' if self.config.search.enable_vector_search else 'Disabled'}")
                    print(f"   • Database Search: {'Enabled' if self.config.search.enable_database_search else 'Disabled'}")

                elif choice == "6":
                    # Help
                    self.print_help()

                else:
                    print("❌ Invalid choice. Please enter a number from 0 to 6.")

            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user")
                print("👋 Goodbye!")
                break

            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                logger.exception("Error details:")
                print("\nPress Enter to continue...")
                input()


def main():
    """Main entry point"""
    try:
        app = ConsoleSearchApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("Fatal error details:")
        sys.exit(1)


if __name__ == "__main__":
    main()
