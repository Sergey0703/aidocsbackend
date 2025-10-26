#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Answer Generation with new RAG Q&A system
Tests query "what VRN we have" to verify natural language answer generation
"""

import requests
import json
import time

API_URL = "http://localhost:8000/api/search/"

test_queries = [
    "what VRN we have",
    "231-D-54321",
    "tell me about Ford Transit",
    "who is the owner of the vehicle",
]

print("=" * 80)
print("TESTING ANSWER GENERATION (RAG Q&A)")
print("=" * 80)

for query in test_queries:
    print(f"\n{'=' * 80}")
    print(f"Query: \"{query}\"")
    print("=" * 80)

    try:
        start_time = time.time()
        response = requests.post(
            API_URL,
            json={"query": query},
            timeout=30
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"\nStatus: SUCCESS ({response.status_code})")
            print(f"Time: {elapsed:.2f}s")
            print(f"\n{'-' * 80}")
            print("ANSWER:")
            print("-" * 80)
            if result.get('answer'):
                print(result['answer'])
            else:
                print("(No answer generated)")

            print(f"\n{'-' * 80}")
            print(f"Source Documents: {result.get('total_results', 0)}")
            print("-" * 80)
            for i, doc in enumerate(result.get('results', [])[:3], 1):
                print(f"\n[{i}] {doc['filename']} (score: {doc['score']:.3f})")
                print(f"    {doc['content'][:150]}...")

            print(f"\n{'-' * 80}")
            print("Metadata:")
            print("-" * 80)
            metadata = result.get('metadata', {})
            print(f"  Retrieval methods: {metadata.get('retrieval_methods', [])}")
            print(f"  Has answer: {metadata.get('has_answer', False)}")
            print(f"  Answer time: {metadata.get('answer_time', 0):.3f}s")
            print(f"  Total time: {result.get('search_time', 0):.3f}s")

        else:
            print(f"\nStatus: ERROR ({response.status_code})")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"\nERROR: {e}")

print(f"\n{'=' * 80}")
print("TEST COMPLETE")
print("=" * 80)
