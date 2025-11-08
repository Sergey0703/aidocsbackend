#!/usr/bin/env python3
"""Debug script to see what the aggregation query is retrieving"""

import requests
import json

API_URL = "http://localhost:8000/api/search/"
query = "how many cars we have?"

print(f"Testing query: '{query}'")
print("-" * 80)

response = requests.post(
    API_URL,
    json={"query": query},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    data = response.json()

    print(f"\nAnswer: {data.get('answer', 'N/A')}")
    print(f"\nNumber of results: {len(data.get('results', []))}")
    print("\nResults details:")
    print("-" * 80)

    for i, result in enumerate(data.get('results', []), 1):
        print(f"\n[{i}] {result.get('filename', 'N/A')}")
        print(f"    Source: {result.get('metadata', {}).get('source_method', 'N/A')}")
        print(f"    Score: {result.get('score', 'N/A')}")
        print(f"    Dedup status: {result.get('metadata', {}).get('dedup_status', 'N/A')}")
        print(f"    Content preview: {result.get('content', '')[:150]}...")

    print("\n" + "=" * 80)
    print("Full response saved to debug_agg_response.json")

    with open("debug_agg_response.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

else:
    print(f"Error: {response.status_code}")
    print(response.text)
