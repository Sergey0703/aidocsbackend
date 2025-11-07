#!/usr/bin/env python3
"""Analyze chunks for VRN detection"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import re

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

# VRN pattern (Irish registration format)
vrn_pattern = r'\b\d{2,3}[-\s]?[A-Z][-\s]?\d{4,5}\b'

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    print("\n" + "="*80)
    print("ANALYZING CHUNKS FOR VRN: 231-D-54321")
    print("="*80 + "\n")

    # Get the latest VCR.docx registry entry
    cur.execute("""
        SELECT id, original_filename, markdown_file_path
        FROM vecs.document_registry
        WHERE original_filename = 'VCR.docx'
        ORDER BY uploaded_at DESC
        LIMIT 1
    """)

    registry = cur.fetchone()

    if not registry:
        print("No VCR.docx found in registry!")
        exit(1)

    print(f"Registry ID: {registry['id']}")
    print(f"Filename: {registry['original_filename']}")
    print(f"Markdown: {registry['markdown_file_path']}")
    print()

    # Get chunks for this document
    cur.execute("""
        SELECT
            id,
            metadata,
            LENGTH(metadata::text) as content_length
        FROM vecs.documents
        WHERE registry_id = %s
        ORDER BY id
    """, (str(registry['id']),))

    chunks = cur.fetchall()

    print(f"Total chunks: {len(chunks)}")
    print("="*80)

    # Analyze each chunk
    for idx, chunk in enumerate(chunks, 1):
        metadata = chunk['metadata']

        # Extract text from metadata (it's stored as JSONB)
        # The structure might be different, let's check
        text = None
        if isinstance(metadata, dict):
            # Try different possible keys
            text = metadata.get('text') or metadata.get('content') or metadata.get('chunk_text')

        if text:
            # Check if VRN is in this chunk
            vrn_found = re.search(vrn_pattern, text, re.IGNORECASE)

            print(f"\nChunk #{idx}:")
            print(f"  Length: {len(text)} chars")
            print(f"  VRN found: {'YES - ' + vrn_found.group() if vrn_found else 'NO'}")
            print(f"  Preview: {text[:150]}...")

            if vrn_found:
                print(f"  >>> VRN CONTEXT:")
                # Show 100 chars before and after VRN
                start = max(0, vrn_found.start() - 100)
                end = min(len(text), vrn_found.end() + 100)
                context = text[start:end]
                print(f"      ...{context}...")
        else:
            print(f"\nChunk #{idx}:")
            print(f"  WARNING: Could not extract text from metadata")
            print(f"  Metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")
            print(f"  Metadata sample: {str(metadata)[:200]}...")

    # Check if VRN is in extracted_data
    print("\n" + "="*80)
    print("CHECKING EXTRACTED_DATA IN REGISTRY")
    print("="*80 + "\n")

    cur.execute("""
        SELECT extracted_data
        FROM vecs.document_registry
        WHERE id = %s
    """, (str(registry['id']),))

    result = cur.fetchone()
    if result and result['extracted_data']:
        extracted = result['extracted_data']
        print(f"Extracted data: {extracted}")
        vrn = extracted.get('vrn') if isinstance(extracted, dict) else None
        print(f"VRN in extracted_data: {vrn}")
    else:
        print("No extracted_data found")

conn.close()
