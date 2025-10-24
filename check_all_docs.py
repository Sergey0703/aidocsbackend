#!/usr/bin/env python3
"""Check all documents regardless of status"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    # Get all documents with chunk counts
    cur.execute("""
        SELECT
            dr.id,
            dr.original_filename,
            dr.status,
            dr.storage_status,
            dr.markdown_file_path,
            COUNT(d.id) as chunk_count
        FROM vecs.document_registry dr
        LEFT JOIN vecs.documents d ON d.registry_id = dr.id
        GROUP BY dr.id, dr.original_filename, dr.status, dr.storage_status, dr.markdown_file_path
        HAVING COUNT(d.id) > 0
        ORDER BY COUNT(d.id) DESC
    """)

    docs = cur.fetchall()

    print(f"\nFound {len(docs)} documents with chunks:\n")

    for idx, doc in enumerate(docs, 1):
        print(f"{idx}. {doc['original_filename'] or 'Unknown'}")
        print(f"   Chunks: {doc['chunk_count']}")
        print(f"   Status: {doc['status']}")
        print(f"   Storage status: {doc['storage_status']}")
        print(f"   Registry ID: {doc['id']}")
        print()

conn.close()
