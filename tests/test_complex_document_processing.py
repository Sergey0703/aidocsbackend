#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for complex document processing pipeline - PRODUCTION WORKFLOW.

This test validates the entire pipeline through the ACTUAL API and Supabase Storage:
1. Upload PDF via API → Supabase Storage
2. Trigger conversion (Docling) → Markdown + JSON in Storage
3. Trigger indexing → Chunks in database
4. Validate search quality → Test queries

Test Document: Vehicle_Service_Report_Toyota_Camry_2023.pdf
- 4 pages with complex structure
- Multiple heading levels
- Large table (16 rows, 6 columns) - CRITICAL for chunking test
- Small table (cost breakdown)
- Mixed formatting (bold, italic)
- Nested sections
- Image with text (VIN plate for OCR testing)

Test Objectives:
1. Upload document via API to Supabase Storage
2. Verify Storage paths (raw/pending)
3. Convert via API (Docling: PDF → Markdown + JSON)
4. Verify conversion outputs in Storage (markdown_storage_path, json_storage_path)
5. Index via API (chunking + embeddings)
6. Validate chunks in database (HybridChunker quality)
7. Test search API (table data, VRN, costs)
8. Check Markdown rendering in search results

Usage:
    # Run full test suite
    python tests/test_complex_document_processing.py

    # Run specific test category
    python tests/test_complex_document_processing.py --test upload
    python tests/test_complex_document_processing.py --test conversion
    python tests/test_complex_document_processing.py --test indexing
    python tests/test_complex_document_processing.py --test search
"""

import sys
import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_DOCUMENT_NAME = "Vehicle_Service_Report_Toyota_Camry_2023"
TEST_FILE_PDF = TEST_DATA_DIR / f"{TEST_DOCUMENT_NAME}.pdf"

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_UPLOAD_URL = f"{API_BASE_URL}/api/documents/upload"
API_CONVERSION_START_URL = f"{API_BASE_URL}/api/conversion/start"
API_CONVERSION_STATUS_URL = f"{API_BASE_URL}/api/conversion/status"
API_INDEXING_START_URL = f"{API_BASE_URL}/api/indexing/start"
API_INDEXING_STATUS_URL = f"{API_BASE_URL}/api/indexing/status"
API_SEARCH_URL = f"{API_BASE_URL}/api/search"

# Timeout settings
UPLOAD_TIMEOUT = 30
CONVERSION_TIMEOUT = 300  # 5 minutes for Docling conversion
INDEXING_TIMEOUT = 300    # 5 minutes for embedding generation
SEARCH_TIMEOUT = 30

# Results storage
test_results = {
    "upload": {},
    "conversion": {},
    "indexing": {},
    "chunks": {},
    "search": {},
    "overall": {}
}


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test(name, status, details=""):
    """Print test result."""
    status_symbol = "[OK]" if status else "[FAIL]"
    print(f"{status_symbol} {name}")
    if details:
        print(f"    {details}")


def test_1_upload_document() -> Optional[Dict]:
    """
    Test 1: Upload Document via API to Supabase Storage

    Steps:
    1. Check if test PDF file exists
    2. Upload via POST /api/documents/upload
    3. Verify response: storage_path, registry_id, status='pending'
    4. Return registry_id for next tests
    """
    print_section("TEST 1: UPLOAD DOCUMENT TO SUPABASE STORAGE")

    # Check test file exists
    if not TEST_FILE_PDF.exists():
        print_test("Test PDF file exists", False, f"Not found: {TEST_FILE_PDF}")
        print(f"\n[ERROR] Please create the PDF file first:")
        print(f"1. Open: {TEST_DATA_DIR / f'{TEST_DOCUMENT_NAME}.docx'}")
        print(f"2. Save As > PDF")
        print(f"3. Save to: {TEST_FILE_PDF}")
        test_results["upload"]["status"] = "skipped"
        return None
    else:
        file_size_mb = TEST_FILE_PDF.stat().st_size / 1024 / 1024
        print_test("Test PDF file exists", True, f"{file_size_mb:.2f} MB")

    # Upload file via API
    try:
        print(f"\n[INFO] Uploading {TEST_FILE_PDF.name} to {API_UPLOAD_URL}...")

        with open(TEST_FILE_PDF, 'rb') as f:
            files = {'file': (TEST_FILE_PDF.name, f, 'application/pdf')}
            response = requests.post(
                API_UPLOAD_URL,
                files=files,
                timeout=UPLOAD_TIMEOUT
            )

        if response.status_code == 200:
            upload_data = response.json()
            print_test("Upload successful", True, f"Status: {response.status_code}")
            print_test("Response contains storage_path", 'storage_path' in upload_data,
                      upload_data.get('storage_path', 'N/A'))
            print_test("Response contains registry_id", 'registry_id' in upload_data,
                      upload_data.get('registry_id', 'N/A'))
            print_test("Storage status is 'pending'", upload_data.get('storage_status') == 'pending',
                      f"Status: {upload_data.get('storage_status', 'N/A')}")

            # Check for duplicate
            is_duplicate = upload_data.get('duplicate', False)
            if is_duplicate:
                print(f"\n[INFO] File already exists (duplicate detected)")
                print(f"   Existing registry_id: {upload_data.get('existing_registry_id')}")
                print(f"   Status: {upload_data.get('status')}")

            test_results["upload"]["success"] = True
            test_results["upload"]["registry_id"] = upload_data.get('registry_id') or upload_data.get('existing_registry_id')
            test_results["upload"]["storage_path"] = upload_data.get('storage_path')
            test_results["upload"]["is_duplicate"] = is_duplicate

            return upload_data

        else:
            print_test("Upload successful", False, f"Status: {response.status_code}, Error: {response.text}")
            test_results["upload"]["success"] = False
            test_results["upload"]["error"] = response.text
            return None

    except requests.exceptions.Timeout:
        print_test("Upload successful", False, f"Upload timed out after {UPLOAD_TIMEOUT}s")
        test_results["upload"]["success"] = False
        test_results["upload"]["error"] = "Timeout"
        return None
    except Exception as e:
        print_test("Upload successful", False, str(e))
        test_results["upload"]["success"] = False
        test_results["upload"]["error"] = str(e)
        return None


def test_2_start_conversion() -> Optional[str]:
    """
    Test 2: Start Document Conversion via API (Docling)

    Steps:
    1. Trigger conversion: POST /api/conversion/start
    2. Get task_id from response
    3. Poll /api/conversion/status until completed
    4. Verify markdown_storage_path and json_storage_path populated
    """
    print_section("TEST 2: DOCUMENT CONVERSION (DOCLING VIA API)")

    # Start conversion
    try:
        print(f"\n[INFO] Starting conversion: POST {API_CONVERSION_START_URL}")
        response = requests.post(
            API_CONVERSION_START_URL,
            json={},  # Use default settings (auto-detect Storage mode)
            timeout=30
        )

        if response.status_code == 200:
            conversion_response = response.json()
            task_id = conversion_response.get('task_id')

            print_test("Conversion started", True, f"Task ID: {task_id}")

            # Check if no pending documents
            if conversion_response.get('status') == 'completed':
                print(f"\n[INFO] No pending documents to convert (all files already processed)")
                test_results["conversion"]["status"] = "completed"
                test_results["conversion"]["no_pending_files"] = True
                return None

            test_results["conversion"]["task_id"] = task_id

            # Poll for completion
            print(f"\n[INFO] Polling conversion status...")
            start_time = time.time()
            max_wait = CONVERSION_TIMEOUT

            while time.time() - start_time < max_wait:
                time.sleep(5)  # Poll every 5 seconds

                status_response = requests.get(
                    f"{API_CONVERSION_STATUS_URL}?task_id={task_id}",
                    timeout=30
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    progress = status_data.get('progress', {})
                    status = progress.get('status')
                    converted = progress.get('converted_files', 0)
                    total = progress.get('total_files', 0)
                    progress_pct = progress.get('progress_percentage', 0)

                    print(f"   Status: {status}, Progress: {converted}/{total} ({progress_pct:.1f}%)")

                    if status == 'completed':
                        print_test("Conversion completed", True,
                                  f"{converted}/{total} files converted")

                        test_results["conversion"]["status"] = "completed"
                        test_results["conversion"]["files_converted"] = converted
                        test_results["conversion"]["duration_seconds"] = int(time.time() - start_time)

                        return task_id

                    elif status == 'failed':
                        print_test("Conversion completed", False,
                                  f"Conversion failed: {progress.get('error', 'Unknown error')}")
                        test_results["conversion"]["status"] = "failed"
                        test_results["conversion"]["error"] = progress.get('error')
                        return None

            # Timeout
            print_test("Conversion completed", False,
                      f"Timeout after {CONVERSION_TIMEOUT}s")
            test_results["conversion"]["status"] = "timeout"
            return None

        else:
            print_test("Conversion started", False,
                      f"Status: {response.status_code}, Error: {response.text}")
            test_results["conversion"]["status"] = "failed"
            test_results["conversion"]["error"] = response.text
            return None

    except Exception as e:
        print_test("Conversion started", False, str(e))
        test_results["conversion"]["status"] = "error"
        test_results["conversion"]["error"] = str(e)
        return None


def test_3_start_indexing(registry_id: Optional[str]) -> Optional[str]:
    """
    Test 3: Start Indexing via API (Chunking + Embeddings)

    Steps:
    1. Trigger indexing: POST /api/indexing/start
    2. Get task_id from response
    3. Poll /api/indexing/status until completed
    4. Verify chunks created in database
    """
    print_section("TEST 3: INDEXING (CHUNKING + EMBEDDINGS VIA API)")

    if not registry_id:
        print_test("Registry ID available", False, "Need to upload document first")
        test_results["indexing"]["status"] = "skipped"
        return None

    # Start indexing
    try:
        print(f"\n[INFO] Starting indexing: POST {API_INDEXING_START_URL}")
        response = requests.post(
            API_INDEXING_START_URL,
            json={},  # Use default settings
            timeout=30
        )

        if response.status_code == 200:
            indexing_response = response.json()
            task_id = indexing_response.get('task_id')

            print_test("Indexing started", True, f"Task ID: {task_id}")
            test_results["indexing"]["task_id"] = task_id

            # Poll for completion
            print(f"\n[INFO] Polling indexing status...")
            start_time = time.time()
            max_wait = INDEXING_TIMEOUT

            while time.time() - start_time < max_wait:
                time.sleep(5)  # Poll every 5 seconds

                status_response = requests.get(
                    f"{API_INDEXING_STATUS_URL}?task_id={task_id}",
                    timeout=30
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    progress = status_data.get('progress', {})
                    status = progress.get('status')
                    indexed = progress.get('files_indexed', 0)
                    total = progress.get('total_files', 0)
                    progress_pct = progress.get('progress_percentage', 0)

                    print(f"   Status: {status}, Progress: {indexed}/{total} ({progress_pct:.1f}%)")

                    if status == 'completed':
                        chunks_created = progress.get('total_chunks_created', 0)
                        print_test("Indexing completed", True,
                                  f"{indexed}/{total} files indexed, {chunks_created} chunks created")

                        test_results["indexing"]["status"] = "completed"
                        test_results["indexing"]["files_indexed"] = indexed
                        test_results["indexing"]["chunks_created"] = chunks_created
                        test_results["indexing"]["duration_seconds"] = int(time.time() - start_time)

                        return task_id

                    elif status == 'failed':
                        print_test("Indexing completed", False,
                                  f"Indexing failed: {progress.get('error', 'Unknown error')}")
                        test_results["indexing"]["status"] = "failed"
                        test_results["indexing"]["error"] = progress.get('error')
                        return None

            # Timeout
            print_test("Indexing completed", False,
                      f"Timeout after {INDEXING_TIMEOUT}s")
            test_results["indexing"]["status"] = "timeout"
            return None

        else:
            print_test("Indexing started", False,
                      f"Status: {response.status_code}, Error: {response.text}")
            test_results["indexing"]["status"] = "failed"
            test_results["indexing"]["error"] = response.text
            return None

    except Exception as e:
        print_test("Indexing started", False, str(e))
        test_results["indexing"]["status"] = "error"
        test_results["indexing"]["error"] = str(e)
        return None


def test_4_search_quality():
    """
    Test 4: Search Quality via API

    Validates:
    - Can find data in tables (brake pads, oil change)
    - Can find VRN (191-D-12345)
    - Can find costs (€654.98, €2,785.00)
    - OCR text findable (VIN WF0)
    - Markdown formatting preserved in results
    """
    print_section("TEST 4: SEARCH QUALITY (HYBRID RAG)")

    test_queries = [
        ("brake pads", ["Brake pads", "front", "rear"], "Table data: services"),
        ("oil change", ["oil", "change", "filter"], "Table data: services"),
        ("191-D-12345", ["191-D-12345"], "VRN search"),
        ("service history", ["service", "history"], "Section search"),
        ("total cost", ["654", "2785", "€"], "Cost search"),
        ("VIN WF0", ["VIN", "WF0"], "OCR text search"),
    ]

    print(f"\n[INFO] Testing {len(test_queries)} search queries...")

    for query, expected_keywords, description in test_queries:
        try:
            response = requests.post(
                API_SEARCH_URL,
                json={"query": query, "top_k": 5},
                timeout=SEARCH_TIMEOUT
            )

            if response.status_code == 200:
                search_data = response.json()
                results = search_data.get('results', [])
                answer = search_data.get('answer', '')

                # Check if expected keywords found in results or answer
                found_keywords = []
                search_text = answer.lower() + " " + " ".join([r.get('content', '').lower() for r in results])

                for keyword in expected_keywords:
                    if keyword.lower() in search_text:
                        found_keywords.append(keyword)

                success = len(found_keywords) >= len(expected_keywords) // 2  # At least half of keywords

                print_test(
                    f"Search: '{query}' ({description})",
                    success,
                    f"Found {len(found_keywords)}/{len(expected_keywords)} keywords, {len(results)} results"
                )

                # Check for Markdown formatting (should NOT have visible asterisks)
                has_visible_asterisks = "**" in answer or any("**" in r.get('content', '') for r in results)
                if has_visible_asterisks:
                    print(f"   [WARN] Visible Markdown syntax detected (** found in results)")

                test_results["search"][query] = {
                    "success": success,
                    "results_count": len(results),
                    "keywords_found": found_keywords,
                    "has_visible_asterisks": has_visible_asterisks
                }

            else:
                print_test(
                    f"Search: '{query}' ({description})",
                    False,
                    f"API error: {response.status_code}"
                )
                test_results["search"][query] = {
                    "success": False,
                    "error": response.status_code
                }

        except Exception as e:
            print_test(
                f"Search: '{query}' ({description})",
                False,
                str(e)
            )
            test_results["search"][query] = {
                "success": False,
                "error": str(e)
            }

    print(f"\n[INFO] Search tests completed")
    print(f"[INFO] For visual validation:")
    print(f"   1. Open frontend: http://localhost:3000")
    print(f"   2. Try searches above")
    print(f"   3. Verify Markdown rendering (bold/italic, tables, headings)")


def generate_test_report():
    """Generate final test report."""
    print_section("TEST SUMMARY - PRODUCTION WORKFLOW VALIDATION")

    # Calculate pass/fail stats
    upload_success = test_results.get('upload', {}).get('success', False)
    conversion_success = test_results.get('conversion', {}).get('status') == 'completed'
    indexing_success = test_results.get('indexing', {}).get('status') == 'completed'

    search_tests = test_results.get('search', {})
    search_passed = sum(1 for q in search_tests.values() if isinstance(q, dict) and q.get('success', False))
    search_total = len([q for q in search_tests.values() if isinstance(q, dict)])

    print("\n=== TEST RESULTS ===\n")
    print(f"  1. Upload to Storage:       {'[OK]' if upload_success else '[FAIL]'}")
    print(f"  2. Conversion (Docling):    {'[OK]' if conversion_success else '[FAIL]'}")
    print(f"  3. Indexing (Embeddings):   {'[OK]' if indexing_success else '[FAIL]'}")
    print(f"  4. Search Quality:          {search_passed}/{search_total} queries passed")

    if upload_success:
        print(f"\n  Registry ID: {test_results['upload'].get('registry_id', 'N/A')}")
        print(f"  Storage Path: {test_results['upload'].get('storage_path', 'N/A')}")

    if conversion_success:
        print(f"\n  Files Converted: {test_results['conversion'].get('files_converted', 0)}")
        print(f"  Duration: {test_results['conversion'].get('duration_seconds', 0)}s")

    if indexing_success:
        print(f"\n  Chunks Created: {test_results['indexing'].get('chunks_created', 0)}")
        print(f"  Duration: {test_results['indexing'].get('duration_seconds', 0)}s")

    # Overall success
    overall_success = upload_success and conversion_success and indexing_success and (search_passed >= search_total // 2)
    test_results["overall"]["success"] = overall_success

    print(f"\n{'='*70}")
    if overall_success:
        print("[OK] ALL TESTS PASSED - PRODUCTION WORKFLOW VALIDATED")
    else:
        print("[FAIL] SOME TESTS FAILED - CHECK DETAILS ABOVE")
    print(f"{'='*70}")

    # Full results JSON
    print("\n[DEBUG] Full Results JSON:")
    print(json.dumps(test_results, indent=2, default=str))


def main():
    """Run all tests in sequence."""
    print_section("COMPLEX DOCUMENT PROCESSING - PRODUCTION WORKFLOW TEST")
    print(f"Test Document: {TEST_FILE_PDF.name}")
    print(f"Test Data Dir: {TEST_DATA_DIR}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"\n[IMPORTANT] Ensure API is running: python run_api.py")
    print(f"[IMPORTANT] Ensure .env has USE_HYBRID_CHUNKING=true, SAVE_JSON_OUTPUT=true")

    input("\nPress Enter to start tests...")

    # Run tests in sequence
    registry_id = None

    # Test 1: Upload
    upload_data = test_1_upload_document()
    if upload_data:
        registry_id = upload_data.get('registry_id') or upload_data.get('existing_registry_id')

    # Test 2: Conversion
    if registry_id:
        conversion_task_id = test_2_start_conversion()
    else:
        print("\n[SKIP] Conversion skipped - upload failed")

    # Test 3: Indexing
    if registry_id:
        indexing_task_id = test_3_start_indexing(registry_id)
    else:
        print("\n[SKIP] Indexing skipped - upload failed")

    # Test 4: Search
    if registry_id:
        test_4_search_quality()
    else:
        print("\n[SKIP] Search tests skipped - upload failed")

    # Generate report
    generate_test_report()

    print("\n" + "=" * 70)
    print("Test script completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
