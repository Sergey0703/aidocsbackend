#!/usr/bin/env python3
"""Quick script to check document_registry data"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

# Load environment
load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    cur.execute("""
        SELECT
            id,
            original_filename,
            raw_file_path,
            status,
            storage_status,
            storage_path,
            uploaded_at
        FROM vecs.document_registry
        WHERE status = 'processed'
        ORDER BY uploaded_at DESC
        LIMIT 5
    """)

    results = cur.fetchall()

    print(f"\n{'='*80}")
    print(f"Found {len(results)} documents with status='processed'")
    print(f"{'='*80}\n")

    for idx, row in enumerate(results, 1):
        print(f"Document #{idx}:")
        print(f"  ID: {row['id']}")
        print(f"  original_filename: {row['original_filename']}")
        print(f"  raw_file_path: {row['raw_file_path']}")
        print(f"  status: {row['status']}")
        print(f"  storage_status: {row['storage_status']}")
        print(f"  storage_path: {row['storage_path']}")
        print(f"  uploaded_at: {row['uploaded_at']}")
        print()

conn.close()
