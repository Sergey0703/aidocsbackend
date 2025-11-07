#!/usr/bin/env python3
"""Check actual chunks in database for CVRT document"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
from collections import Counter

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    # Find CVRT document registry
    cur.execute("""
        SELECT id, original_filename, markdown_file_path
        FROM vecs.document_registry
        WHERE LOWER(original_filename) LIKE '%cvrt%'
        ORDER BY uploaded_at DESC
        LIMIT 1
    """)

    registry = cur.fetchone()

    if not registry:
        print("No CVRT document found!")
        exit(1)

    registry_id = registry['id']
    print(f"\n{'='*80}")
    print(f"CVRT DOCUMENT IN DATABASE")
    print(f"{'='*80}\n")
    print(f"Registry ID: {registry_id}")
    print(f"Filename: {registry['original_filename']}")
    print(f"Markdown path: {registry['markdown_file_path']}")
    print()

    # Get all chunks for this document
    cur.execute("""
        SELECT
            id,
            metadata->>'text' as text,
            metadata->>'chunking_method' as chunking_method,
            metadata->>'chunk_type' as chunk_type,
            LENGTH(metadata->>'text') as text_length
        FROM vecs.documents
        WHERE registry_id = %s
        ORDER BY id
    """, (str(registry_id),))

    chunks = cur.fetchall()

    print(f"{'='*80}")
    print(f"CHUNK ANALYSIS")
    print(f"{'='*80}\n")
    print(f"Total chunks in database: {len(chunks)}")

    if len(chunks) == 0:
        print("No chunks found!")
        exit(0)

    # Analyze chunking method
    methods = [c.get('chunking_method') for c in chunks]
    method_counts = Counter(methods)
    print(f"\nChunking methods:")
    for method, count in method_counts.items():
        print(f"  {method}: {count} chunks")

    # Analyze chunk types
    types = [c.get('chunk_type') for c in chunks]
    type_counts = Counter(types)
    print(f"\nChunk types:")
    for chunk_type, count in type_counts.items():
        print(f"  {chunk_type}: {count} chunks")

    # Check for duplicates
    chunk_texts = [c['text'] for c in chunks if c['text']]
    unique_texts = set(chunk_texts)
    print(f"\nDuplicate analysis:")
    print(f"  Total chunks: {len(chunk_texts)}")
    print(f"  Unique chunks: {len(unique_texts)}")
    print(f"  Duplicate chunks: {len(chunk_texts) - len(unique_texts)}")

    # Find most duplicated
    text_counts = Counter(chunk_texts)
    most_common = text_counts.most_common(10)
    print(f"\nTop 10 most duplicated chunks:")
    for i, (text, count) in enumerate(most_common, 1):
        if count > 1:
            print(f"  {i}. Appears {count} times: {text[:80]}...")

    # Length statistics
    lengths = [c['text_length'] for c in chunks if c['text_length']]
    if lengths:
        print(f"\nChunk length statistics:")
        print(f"  Min: {min(lengths)} chars")
        print(f"  Max: {max(lengths)} chars")
        print(f"  Avg: {sum(lengths) / len(lengths):.0f} chars")

    # Sample first 10 chunks
    print(f"\n{'='*80}")
    print(f"FIRST 10 CHUNKS")
    print(f"{'='*80}\n")
    for i, chunk in enumerate(chunks[:10], 1):
        text = chunk['text'] or 'NULL'
        text_len = chunk['text_length'] or 0
        method = chunk.get('chunking_method', 'unknown')
        chunk_type = chunk.get('chunk_type', 'unknown')
        print(f"[Chunk {i}] {text_len} chars | method={method} | type={chunk_type}")
        print(f"  {text[:150]}...")
        print()

conn.close()
