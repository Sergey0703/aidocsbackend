#!/usr/bin/env python3
"""Analyze the duplicate document issue"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    print("\n" + "="*80)
    print("DOCUMENT_REGISTRY - All records for 1761317407_VCR.docx")
    print("="*80 + "\n")

    cur.execute("""
        SELECT
            id,
            original_filename,
            status,
            storage_status,
            storage_path,
            markdown_file_path,
            uploaded_at,
            updated_at
        FROM vecs.document_registry
        WHERE original_filename = 'VCR.docx'
           OR markdown_file_path LIKE '%1761317407_VCR%'
        ORDER BY uploaded_at DESC
    """)

    registry_records = cur.fetchall()

    for idx, row in enumerate(registry_records, 1):
        print(f"Record #{idx}:")
        print(f"  ID: {row['id']}")
        print(f"  original_filename: {row['original_filename']}")
        print(f"  status: {row['status']}")
        print(f"  storage_status: {row['storage_status']}")
        print(f"  storage_path: {row['storage_path']}")
        print(f"  markdown_file_path: {row['markdown_file_path']}")
        print(f"  uploaded_at: {row['uploaded_at']}")
        print(f"  updated_at: {row['updated_at']}")
        print()

    print("\n" + "="*80)
    print("DOCUMENTS (CHUNKS) - Count by registry_id")
    print("="*80 + "\n")

    # Get registry IDs
    registry_ids = [str(r['id']) for r in registry_records]

    if registry_ids:
        cur.execute("""
            SELECT
                registry_id,
                COUNT(*) as chunk_count,
                AVG(LENGTH(text)) as avg_chunk_size
            FROM vecs.documents
            WHERE registry_id = ANY(%s)
            GROUP BY registry_id
        """, (registry_ids,))

        chunk_stats = cur.fetchall()

        for stat in chunk_stats:
            # Find matching registry record
            matching = [r for r in registry_records if str(r['id']) == str(stat['registry_id'])]
            filename = matching[0]['original_filename'] if matching else 'Unknown'

            print(f"Registry ID: {stat['registry_id']}")
            print(f"  Filename: {filename}")
            print(f"  Chunks: {stat['chunk_count']}")
            print(f"  Avg chunk size: {int(stat['avg_chunk_size'])} chars")
            print()

    print("\n" + "="*80)
    print("CHUNK DETAILS - First registry_id")
    print("="*80 + "\n")

    if registry_ids:
        cur.execute("""
            SELECT
                id,
                registry_id,
                LENGTH(text) as text_length,
                LEFT(text, 100) as text_preview
            FROM vecs.documents
            WHERE registry_id = %s
            ORDER BY id
            LIMIT 5
        """, (registry_ids[0],))

        chunks = cur.fetchall()

        for idx, chunk in enumerate(chunks, 1):
            print(f"Chunk #{idx}:")
            print(f"  ID: {chunk['id']}")
            print(f"  Length: {chunk['text_length']} chars")
            print(f"  Preview: {chunk['text_preview']}...")
            print()

conn.close()
