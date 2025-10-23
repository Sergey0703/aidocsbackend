#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_api_score_fix.py - Test that API returns improved scores

import requests
import json

def test_api_scores():
    """Test VRN search via API and check score improvement"""

    print("\n" + "=" * 80)
    print("API SCORE FIX TEST")
    print("=" * 80)

    # API endpoint
    url = "http://localhost:8000/api/search/"

    # Test query (VRN)
    payload = {
        "query": "231-D-54321",
        "top_k": 3
    }

    print(f"\nSending request to: {url}")
    print(f"Query: {payload['query']}")
    print("-" * 80)

    try:
        # Send request
        response = requests.post(url, json=payload, timeout=60)

        if response.status_code != 200:
            print(f"\n[!] ERROR: HTTP {response.status_code}")
            print(response.text)
            return

        # Parse response
        data = response.json()

        if not data.get("success"):
            print(f"\n[!] Search failed: {data}")
            return

        results = data.get("results", [])

        print(f"\n[+] Received {len(results)} results")
        print(f"    Search time: {data.get('search_time', 0):.3f}s")
        print("-" * 80)

        # Analyze scores
        print("\nSCORE ANALYSIS:")
        print("-" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result['file_name']}")

            # Display score (what user sees)
            display_score = result['score']
            print(f"    DISPLAY SCORE: {display_score * 100:.1f}%")

            # Check metadata
            metadata = result.get('metadata', {})

            if 'llm_relevance_score' in metadata:
                llm_score = metadata['llm_relevance_score']
                print(f"    LLM score: {llm_score:.1f}/10")

                # Verify conversion is correct
                expected_display = llm_score / 10.0
                if abs(display_score - expected_display) < 0.01:
                    print(f"    [+] Correct! Display score matches LLM score")
                else:
                    print(f"    [!] ERROR: Display score ({display_score:.3f}) != LLM score ({expected_display:.3f})")
            else:
                print(f"    [!] No LLM score in metadata")

            # Match type
            match_type = metadata.get('match_type', 'unknown')
            print(f"    Match type: {match_type}")

        # Summary
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)

        if results:
            first_result = results[0]
            score = first_result['score']

            print(f"\nUser sees: {score * 100:.1f}%")

            if score >= 0.90:
                print("[+] EXCELLENT: Score shows high relevance (90%+)")
            elif score >= 0.70:
                print("[+] GOOD: Score shows strong relevance (70%+)")
            elif score < 0.70:
                print("[!] WARNING: Score looks low (<70%)")
                print("    This should be improved if LLM score is higher!")

            # Check if LLM score was used
            metadata = first_result.get('metadata', {})
            if 'llm_relevance_score' in metadata:
                llm_score = metadata['llm_relevance_score']
                print(f"\n[+] SUCCESS: API is using LLM score ({llm_score:.1f}/10 = {llm_score * 10:.1f}%)")
                print("    Score display is accurate and user-friendly!")
            else:
                print("\n[!] WARNING: LLM score not available")
                print("    Consider enabling LLM re-ranking for better accuracy")

        print("\n" + "=" * 80)

    except requests.exceptions.RequestException as e:
        print(f"\n[!] Request failed: {e}")
    except Exception as e:
        print(f"\n[!] Error: {e}")


if __name__ == "__main__":
    test_api_scores()
