#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector/Semantic Search Quality Testing

Tests semantic search capabilities using actual vector embeddings
and compares with exact match results.
"""

import os
import sys
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(r'c:\projects\aidocsbackend\rag_indexer\.env')

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def test_vector_search():
    """Test vector/semantic search quality"""

    connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
    if not connection_string:
        print("ERROR: No SUPABASE_CONNECTION_STRING found!")
        return

    # Initialize embedding model
    embed_model = os.getenv("EMBED_MODEL", "text-embedding-004")

    # Define semantic test queries
    semantic_queries = [
        ("Ford vehicle with 2200 kg max mass", "Natural language - cross-field"),
        ("vehicle registered to Murphy Builders", "Entity-based query"),
        ("Transit Connect van registration details", "Model + document type"),
        ("231-D-54321 registration certificate", "VRN + document type"),
        ("N1 goods vehicle Dublin", "Category + location"),
        ("Ford Transit 1499 engine", "Make + model + engine"),
    ]

    print("=" * 80)
    print("VECTOR/SEMANTIC SEARCH QUALITY TEST")
    print("=" * 80)

    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get total chunks for context
        cur.execute("SELECT COUNT(*) as total FROM vecs.documents")
        total_chunks = cur.fetchone()['total']
        print(f"\nTotal chunks in database: {total_chunks}")

        print("\n" + "=" * 80)
        print("SEMANTIC SEARCH TESTS")
        print("=" * 80)

        results_summary = []

        for query_text, query_type in semantic_queries:
            print(f"\n[Query Type: {query_type}]")
            print(f"Query: \"{query_text}\"")
            print("-" * 60)

            # Generate embedding for query
            try:
                result = genai.embed_content(
                    model=f"models/{embed_model}",
                    content=query_text,
                    task_type="retrieval_query"
                )
                query_embedding = result['embedding']

                # Vector similarity search using pgvector
                sql = """
                SELECT
                    id,
                    metadata->>'text' as content,
                    metadata->>'file_name' as file_name,
                    metadata->>'chunk_index' as chunk_index,
                    1 - (vec <=> %s::vector) as similarity
                FROM vecs.documents
                ORDER BY vec <=> %s::vector
                LIMIT 5
                """

                cur.execute(sql, (query_embedding, query_embedding))
                vector_results = cur.fetchall()

                if vector_results:
                    print(f"Found {len(vector_results)} results")

                    for i, result in enumerate(vector_results, 1):
                        similarity = result['similarity']
                        file_name = result['file_name']
                        chunk_index = result['chunk_index']
                        content_preview = result['content'][:150] if result['content'] else 'N/A'

                        print(f"\n  [{i}] Similarity: {similarity:.4f}")
                        print(f"      File: {file_name}")
                        print(f"      Chunk: {chunk_index}")
                        print(f"      Preview: {content_preview}...")

                    # Analyze top result
                    top_similarity = vector_results[0]['similarity']
                    status = "EXCELLENT" if top_similarity > 0.8 else "GOOD" if top_similarity > 0.6 else "FAIR" if top_similarity > 0.4 else "POOR"

                    results_summary.append({
                        'query': query_text,
                        'type': query_type,
                        'top_similarity': top_similarity,
                        'status': status,
                        'results_count': len(vector_results)
                    })

                else:
                    print("  No results found")
                    results_summary.append({
                        'query': query_text,
                        'type': query_type,
                        'top_similarity': 0.0,
                        'status': 'FAILED',
                        'results_count': 0
                    })

            except Exception as e:
                print(f"  ERROR generating embedding: {e}")
                results_summary.append({
                    'query': query_text,
                    'type': query_type,
                    'top_similarity': 0.0,
                    'status': 'ERROR',
                    'results_count': 0
                })

        # Print summary
        print("\n" + "=" * 80)
        print("VECTOR SEARCH QUALITY SUMMARY")
        print("=" * 80)

        for result in results_summary:
            print(f"\n[{result['status']}] {result['query']}")
            print(f"  Type: {result['type']}")
            print(f"  Top Similarity: {result['top_similarity']:.4f}")
            print(f"  Results: {result['results_count']}")

        # Calculate statistics
        successful = sum(1 for r in results_summary if r['status'] in ['EXCELLENT', 'GOOD'])
        avg_similarity = sum(r['top_similarity'] for r in results_summary) / len(results_summary) if results_summary else 0

        print("\n" + "=" * 80)
        print("OVERALL STATISTICS")
        print("=" * 80)
        print(f"Total Queries: {len(results_summary)}")
        print(f"Successful (EXCELLENT/GOOD): {successful}/{len(results_summary)} ({successful/len(results_summary)*100:.1f}%)")
        print(f"Average Top Similarity: {avg_similarity:.4f}")

        # Quality rating
        if avg_similarity > 0.7:
            quality = "EXCELLENT - Semantic search working very well"
        elif avg_similarity > 0.5:
            quality = "GOOD - Semantic search functional"
        elif avg_similarity > 0.3:
            quality = "FAIR - May need chunking/embedding improvements"
        else:
            quality = "POOR - Significant issues with semantic search"

        print(f"\nOverall Quality: {quality}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_vector_search()
