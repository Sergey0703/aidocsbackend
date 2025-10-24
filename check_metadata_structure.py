#!/usr/bin/env python3
"""Check metadata structure in vecs.documents"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import json

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    # Get the latest VCR document
    cur.execute("""
        SELECT id, original_filename
        FROM vecs.document_registry
        WHERE original_filename = 'VCR.docx'
        ORDER BY uploaded_at DESC
        LIMIT 1
    """)

    registry = cur.fetchone()

    if not registry:
        print("No VCR.docx found!")
        exit(1)

    print(f"\nRegistry ID: {registry['id']}")
    print(f"Filename: {registry['original_filename']}")

    # Get one chunk to examine metadata structure
    cur.execute("""
        SELECT
            id,
            registry_id,
            metadata
        FROM vecs.documents
        WHERE registry_id = %s
        LIMIT 1
    """, (str(registry['id']),))

    chunk = cur.fetchone()

    if chunk:
        print(f"\n{'='*80}")
        print("METADATA STRUCTURE:")
        print(f"{'='*80}\n")

        metadata = chunk['metadata']

        print(f"Type: {type(metadata)}")
        print(f"\nKeys: {list(metadata.keys()) if isinstance(metadata, dict) else 'N/A'}")

        print(f"\n{'='*80}")
        print("METADATA CONTENT (formatted):")
        print(f"{'='*80}\n")

        print(json.dumps(metadata, indent=2, ensure_ascii=False)[:1000])

        # Check if we can extract text
        if isinstance(metadata, dict):
            # Try different possible keys
            text_keys = ['text', 'content', 'chunk_text', '_node_content']

            print(f"\n{'='*80}")
            print("TEXT EXTRACTION ATTEMPTS:")
            print(f"{'='*80}\n")

            for key in text_keys:
                if key in metadata:
                    text = metadata[key]
                    print(f"✓ Found text in key '{key}':")
                    print(f"  Type: {type(text)}")
                    print(f"  Length: {len(str(text))}")
                    print(f"  Preview: {str(text)[:200]}...")
                    print()
    else:
        print("No chunks found for this registry_id!")

conn.close()
