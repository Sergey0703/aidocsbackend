#!/usr/bin/env python3
"""Analyze chunking issues - why so many chunks?"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
from pathlib import Path

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    print("\n" + "="*80)
    print("ANALYZING CHUNKING ISSUE")
    print("="*80 + "\n")

    # Get all indexed documents with chunk counts
    cur.execute("""
        SELECT
            dr.id,
            dr.original_filename,
            dr.markdown_file_path,
            dr.uploaded_at,
            COUNT(d.id) as chunk_count
        FROM vecs.document_registry dr
        LEFT JOIN vecs.documents d ON d.registry_id = dr.id
        WHERE dr.status = 'processed'
        GROUP BY dr.id, dr.original_filename, dr.markdown_file_path, dr.uploaded_at
        ORDER BY COUNT(d.id) DESC
    """)

    docs = cur.fetchall()

    print(f"Found {len(docs)} indexed documents:\n")

    for idx, doc in enumerate(docs, 1):
        print(f"{idx}. {doc['original_filename']}")
        print(f"   Chunks: {doc['chunk_count']}")
        print(f"   Registry ID: {doc['id']}")
        print(f"   Markdown: {doc['markdown_file_path']}")
        print()

    # Analyze the document with most chunks
    if docs:
        worst_doc = docs[0]
        print("\n" + "="*80)
        print(f"ANALYZING WORST CASE: {worst_doc['original_filename']}")
        print(f"Registry ID: {worst_doc['id']}")
        print(f"Total chunks: {worst_doc['chunk_count']}")
        print("="*80 + "\n")

        # Check markdown file size
        md_path = worst_doc['markdown_file_path']
        if md_path and os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()

            print(f"Markdown file stats:")
            print(f"  Path: {md_path}")
            print(f"  Size: {len(content)} chars")
            print(f"  Lines: {content.count(chr(10)) + 1}")
            print(f"  Words: {len(content.split())}")
            print()

            print(f"Content preview (first 500 chars):")
            print("-" * 80)
            print(content[:500])
            print("-" * 80)
            print()

        # Sample 10 chunks to see their sizes
        cur.execute("""
            SELECT
                id,
                LENGTH(metadata::text) as metadata_size,
                metadata->>'text' as text,
                LENGTH(metadata->>'text') as text_length
            FROM vecs.documents
            WHERE registry_id = %s
            ORDER BY id
            LIMIT 10
        """, (str(worst_doc['id']),))

        chunks = cur.fetchall()

        print(f"Sample of first 10 chunks:")
        print("-" * 80)
        for i, chunk in enumerate(chunks, 1):
            text_len = chunk['text_length'] if chunk['text_length'] else 0
            text_preview = chunk['text'][:100] if chunk['text'] else 'NULL'
            print(f"Chunk {i}:")
            print(f"  Text length: {text_len} chars")
            print(f"  Preview: {text_preview}...")
            print()

        # Check for duplicate chunks (same text)
        cur.execute("""
            SELECT
                metadata->>'text' as text,
                COUNT(*) as count
            FROM vecs.documents
            WHERE registry_id = %s
            GROUP BY metadata->>'text'
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """, (str(worst_doc['id']),))

        duplicates = cur.fetchall()

        if duplicates:
            print("\n" + "="*80)
            print("DUPLICATE CHUNKS DETECTED!")
            print("="*80 + "\n")
            for dup in duplicates:
                print(f"Text appears {dup['count']} times:")
                print(f"  {dup['text'][:100]}...")
                print()

conn.close()
