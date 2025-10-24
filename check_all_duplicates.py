#!/usr/bin/env python3
"""Check for ALL duplicate registry entries"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    # Find duplicates by markdown_file_path (case-insensitive)
    cur.execute("""
        SELECT
            LOWER(REPLACE(markdown_file_path, '\\', '/')) as normalized_path,
            COUNT(*) as count,
            ARRAY_AGG(id ORDER BY uploaded_at) as ids,
            ARRAY_AGG(original_filename ORDER BY uploaded_at) as filenames,
            ARRAY_AGG(status ORDER BY uploaded_at) as statuses
        FROM vecs.document_registry
        WHERE markdown_file_path IS NOT NULL
        GROUP BY LOWER(REPLACE(markdown_file_path, '\\', '/'))
        HAVING COUNT(*) > 1
    """)

    duplicates = cur.fetchall()

    print("\n" + "="*80)
    print(f"Found {len(duplicates)} sets of duplicate registry entries")
    print("="*80 + "\n")

    if duplicates:
        for dup in duplicates:
            print(f"Path: {dup['normalized_path']}")
            print(f"  Count: {dup['count']}")
            for i, (id, fname, status) in enumerate(zip(dup['ids'], dup['filenames'], dup['statuses']), 1):
                print(f"  #{i}: {id}")
                print(f"       filename: {fname}")
                print(f"       status: {status}")
            print()
    else:
        print("No duplicates found!")

conn.close()
