#!/usr/bin/env python3
"""Check all document statuses"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    # Check all statuses
    cur.execute("""
        SELECT
            status,
            storage_status,
            COUNT(*) as count
        FROM vecs.document_registry
        GROUP BY status, storage_status
        ORDER BY status, storage_status
    """)

    print("\n" + "="*80)
    print("Document Registry Status Summary")
    print("="*80 + "\n")

    for row in cur.fetchall():
        print(f"status='{row['status']}', storage_status='{row['storage_status']}' -> {row['count']} documents")

    print("\n" + "="*80)
    print("Recent documents with storage_status='processed'")
    print("="*80 + "\n")

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
        WHERE storage_status = 'processed'
        ORDER BY uploaded_at DESC
        LIMIT 5
    """)

    results = cur.fetchall()

    for idx, row in enumerate(results, 1):
        print(f"Document #{idx}:")
        print(f"  ID: {row['id']}")
        print(f"  original_filename: {row['original_filename']}")
        print(f"  raw_file_path: {row['raw_file_path']}")
        print(f"  status: {row['status']}")
        print(f"  storage_status: {row['storage_status']}")
        print(f"  storage_path: {row['storage_path']}")
        print()

conn.close()
