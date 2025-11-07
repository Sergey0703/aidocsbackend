#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_detailed_logs.py - Test API and show detailed backend logs

import requests
import time

def test_search_with_logs():
    """
    Send a search request and trigger detailed backend logging
    """
    print("\nSending search request to API...")
    print("Check the API console output for detailed logs!")
    print("-" * 80)

    url = "http://localhost:8000/api/search/"
    payload = {
        "query": "231-D-54321",
        "top_k": 3
    }

    print(f"\nQuery: {payload['query']}")
    print("Waiting for response...\n")

    start = time.time()
    response = requests.post(url, json=payload, timeout=60)
    elapsed = time.time() - start

    print(f"Response received in {elapsed:.3f}s")
    print("-" * 80)

    if response.status_code == 200:
        data = response.json()
        print(f"\nResults: {len(data.get('results', []))}")
        print(f"Total time: {data.get('search_time', 0):.3f}s")

        # Show returned scores
        results = data.get('results', [])
        if results:
            print("\nReturned to frontend:")
            for i, res in enumerate(results[:3], 1):
                print(f"  [{i}] {res['file_name']}: {res['score'] * 100:.1f}%")
    else:
        print(f"\nERROR: HTTP {response.status_code}")
        print(response.text)

    print("\n" + "=" * 80)
    print("CHECK API CONSOLE OUTPUT ABOVE FOR DETAILED BACKEND LOGS")
    print("=" * 80)


if __name__ == "__main__":
    test_search_with_logs()
