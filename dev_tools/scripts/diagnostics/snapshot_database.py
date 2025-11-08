#!/usr/bin/env python3
"""
Database Snapshot Script for RAG Testing

This script connects to the Supabase database and extracts:
- List of all document filenames
- List of all VRNs mentioned in documents
- Document count by type
- Available entities (owners, makes, models)
- Total chunks count

Output is saved to: dev_tools/datasets/ground_truth/database_snapshot.json

This is the foundation for RAG testing - tests must know what data exists.
"""

import os
import json
import psycopg2
from psycopg2 import extras
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv
import re

# Load environment from rag_indexer/.env
load_dotenv('rag_indexer/.env')

def extract_vrns_from_text(text):
    """
    Extract VRN (Vehicle Registration Numbers) from text using regex.

    Irish VRN format examples:
    - 231-D-54321 (modern format: YY-C-Number)
    - 191-D-12345
    - 141-D-98765
    - 06-D-12345 (older format)
    """
    if not text:
        return []

    # Pattern for Irish VRN: digits-letter-digits with optional hyphens
    patterns = [
        r'\b\d{2,3}[-\s]?[A-Z]{1,2}[-\s]?\d{4,6}\b',  # Standard format with hyphens/spaces
        r'\b\d{6,9}\b'  # Pure numeric format (less common)
    ]

    vrns = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        vrns.update([m.upper().replace(' ', '-') for m in matches])

    return list(vrns)

def extract_entities_from_metadata(metadata_list):
    """Extract unique entities (owners, makes, models) from document metadata."""
    owners = set()
    makes = set()
    models = set()

    for metadata in metadata_list:
        if not metadata:
            continue

        # Extract owner information
        owner_fields = ['owner_name', 'registered_owner', 'owner', 'policy_holder']
        for field in owner_fields:
            if field in metadata and metadata[field]:
                owners.add(str(metadata[field]).strip())

        # Extract vehicle make
        make_fields = ['make', 'vehicle_make', 'manufacturer']
        for field in make_fields:
            if field in metadata and metadata[field]:
                makes.add(str(metadata[field]).strip())

        # Extract vehicle model
        model_fields = ['model', 'vehicle_model']
        for field in model_fields:
            if field in metadata and metadata[field]:
                models.add(str(metadata[field]).strip())

    return {
        'owners': sorted(list(owners)),
        'makes': sorted(list(makes)),
        'models': sorted(list(models))
    }

def main():
    print("\n" + "="*80)
    print("DATABASE SNAPSHOT FOR RAG TESTING")
    print("="*80 + "\n")

    # Connect to database
    conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
    if not conn_string:
        print("[ERROR] SUPABASE_CONNECTION_STRING not found in environment")
        return

    print("[*] Connecting to database...")
    try:
        conn = psycopg2.connect(conn_string)
        print("[+] Connected successfully\n")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return

    snapshot_data = {
        "snapshot_date": datetime.now().isoformat(),
        "total_documents": 0,
        "total_chunks": 0,
        "documents": [],
        "vrns": [],
        "entities": {
            "owners": [],
            "makes": [],
            "models": []
        },
        "document_types": {},
        "status_breakdown": {}
    }

    try:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # ================================================================
            # 1. Get all documents from document_registry
            # ================================================================
            print("[*] Querying document_registry...")
            cur.execute("""
                SELECT
                    id,
                    original_filename,
                    document_type,
                    status,
                    extracted_data,
                    vehicle_id,
                    uploaded_at
                FROM vecs.document_registry
                ORDER BY uploaded_at DESC
            """)

            registry_docs = cur.fetchall()
            snapshot_data["total_documents"] = len(registry_docs)

            print(f"[+] Found {len(registry_docs)} documents in registry\n")

            # Track document types and status
            doc_types = Counter()
            statuses = Counter()
            all_metadata = []

            for doc in registry_docs:
                snapshot_data["documents"].append(doc["original_filename"])

                # Count by document type
                doc_type = doc.get("document_type") or "unknown"
                doc_types[doc_type] += 1

                # Count by status
                status = doc.get("status") or "unknown"
                statuses[status] += 1

                # Collect metadata for entity extraction
                if doc.get("extracted_data"):
                    all_metadata.append(doc["extracted_data"])

            snapshot_data["document_types"] = dict(doc_types)
            snapshot_data["status_breakdown"] = dict(statuses)

            # ================================================================
            # 2. Get all chunks from vecs.documents
            # ================================================================
            print("[*] Querying vecs.documents (vector chunks)...")
            cur.execute("""
                SELECT COUNT(*) as total
                FROM vecs.documents
            """)

            chunk_count = cur.fetchone()
            snapshot_data["total_chunks"] = chunk_count["total"] if chunk_count else 0
            print(f"[+] Found {snapshot_data['total_chunks']} chunks in vector database\n")

            # ================================================================
            # 3. Extract VRNs from chunk content
            # ================================================================
            print("[*] Extracting VRNs from document content...")
            cur.execute("""
                SELECT metadata
                FROM vecs.documents
                WHERE metadata IS NOT NULL
                LIMIT 1000
            """)

            chunks = cur.fetchall()
            all_vrns = set()

            for chunk in chunks:
                metadata = chunk.get("metadata", {})

                # Extract VRNs from file_name
                if "file_name" in metadata:
                    vrns = extract_vrns_from_text(metadata["file_name"])
                    all_vrns.update(vrns)

                # Extract VRNs from content if available
                if "content" in metadata:
                    vrns = extract_vrns_from_text(metadata.get("content", ""))
                    all_vrns.update(vrns)

            # Also check registry metadata for VRNs
            for metadata in all_metadata:
                if "vrn" in metadata:
                    all_vrns.add(str(metadata["vrn"]).upper())
                if "registration_number" in metadata:
                    all_vrns.add(str(metadata["registration_number"]).upper())

            snapshot_data["vrns"] = sorted(list(all_vrns))
            print(f"[+] Extracted {len(all_vrns)} unique VRNs\n")

            # ================================================================
            # 4. Extract entities (owners, makes, models)
            # ================================================================
            print("[*] Extracting entities from metadata...")
            entities = extract_entities_from_metadata(all_metadata)
            snapshot_data["entities"] = entities

            print(f"[+] Found entities:")
            print(f"    - Owners: {len(entities['owners'])}")
            print(f"    - Makes: {len(entities['makes'])}")
            print(f"    - Models: {len(entities['models'])}")
            print()

            # ================================================================
            # 5. Get vehicles from vehicles table (if exists)
            # ================================================================
            print("[*] Querying vehicles table...")
            try:
                cur.execute("""
                    SELECT
                        registration_number,
                        vin_number,
                        make,
                        model,
                        current_driver_id
                    FROM vecs.vehicles
                """)

                vehicles = cur.fetchall()

                if vehicles:
                    snapshot_data["vehicles"] = [
                        {
                            "registration_number": v["registration_number"],
                            "vin": v["vin_number"],
                            "make": v["make"],
                            "model": v["model"],
                            "has_driver": v["current_driver_id"] is not None
                        }
                        for v in vehicles
                    ]
                    print(f"[+] Found {len(vehicles)} vehicles in vehicles table\n")
                else:
                    print("[!] No vehicles found in vehicles table\n")

            except Exception as e:
                print(f"[!] Vehicles table query failed (table may not exist): {e}\n")
                snapshot_data["vehicles"] = []

    except Exception as e:
        print(f"[ERROR] Database query failed: {e}")
        conn.close()
        return

    finally:
        conn.close()

    # ================================================================
    # 6. Save snapshot to JSON
    # ================================================================
    output_path = "dev_tools/datasets/ground_truth/database_snapshot.json"

    print(f"[*] Saving snapshot to {output_path}...")
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)

        print(f"[+] Snapshot saved successfully\n")
    except Exception as e:
        print(f"[ERROR] Failed to save snapshot: {e}")
        return

    # ================================================================
    # 7. Print summary
    # ================================================================
    print("="*80)
    print("DATABASE SNAPSHOT SUMMARY")
    print("="*80)
    print(f"Snapshot Date:        {snapshot_data['snapshot_date']}")
    print(f"Total Documents:      {snapshot_data['total_documents']}")
    print(f"Total Chunks:         {snapshot_data['total_chunks']}")
    print(f"Unique VRNs:          {len(snapshot_data['vrns'])}")
    print()

    print("Document Types:")
    for doc_type, count in snapshot_data["document_types"].items():
        print(f"  - {doc_type}: {count}")
    print()

    print("Document Status:")
    for status, count in snapshot_data["status_breakdown"].items():
        print(f"  - {status}: {count}")
    print()

    print("VRNs Found:")
    for vrn in snapshot_data["vrns"][:10]:  # Show first 10
        print(f"  - {vrn}")
    if len(snapshot_data["vrns"]) > 10:
        print(f"  ... and {len(snapshot_data['vrns']) - 10} more")
    print()

    print("Entities:")
    print(f"  Owners ({len(snapshot_data['entities']['owners'])}):")
    for owner in snapshot_data['entities']['owners'][:5]:
        print(f"    - {owner}")
    if len(snapshot_data['entities']['owners']) > 5:
        print(f"    ... and {len(snapshot_data['entities']['owners']) - 5} more")

    print(f"  Makes ({len(snapshot_data['entities']['makes'])}):")
    for make in snapshot_data['entities']['makes']:
        print(f"    - {make}")

    print(f"  Models ({len(snapshot_data['entities']['models'])}):")
    for model in snapshot_data['entities']['models']:
        print(f"    - {model}")
    print()

    print("="*80)
    print(f"[SUCCESS] Snapshot complete! Saved to: {output_path}")
    print("="*80)
    print()
    print("Next Steps:")
    print("1. Review database_snapshot.json to validate available data")
    print("2. Verify ground truth test cases match available VRNs/entities")
    print("3. Run smoke test: python dev_tools/tests/rag_evaluation/smoke_test.py")
    print()

if __name__ == "__main__":
    main()
