#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick script to analyze chunks for VCR.md"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)
cur = conn.cursor()

# Get chunks for VCR.md
cur.execute("""
    SELECT
        id,
        LENGTH(metadata->>'text') as text_length,
        SUBSTRING(metadata->>'text', 1, 200) as preview
    FROM vecs.documents
    WHERE metadata->>'file_name' = 'VCR.md'
    ORDER BY id
""")

results = cur.fetchall()

print("\n" + "="*70)
print("CHUNK ANALYSIS FOR VCR.md")
print("="*70)
print(f"Total chunks: {len(results)}")
print("="*70 + "\n")

total_chars = 0
for i, (chunk_id, text_len, preview) in enumerate(results, 1):
    total_chars += text_len
    print(f"Chunk {i}:")
    print(f"  ID: {chunk_id[:50]}...")
    print(f"  Text length: {text_len} chars")
    print(f"  Preview: {preview}...")
    print()

print("="*70)
print(f"TOTAL: {len(results)} chunks, {total_chars} chars")
print("="*70)

# Also check the original document
cur.execute("""
    SELECT
        COUNT(*) as total_chunks,
        SUM(LENGTH(metadata->>'text')) as total_chars
    FROM vecs.documents
    WHERE metadata->>'file_name' = 'VCR.md'
""")

total_chunks, total_chars_db = cur.fetchone()
print(f"\nDatabase stats:")
print(f"  Total chunks: {total_chunks}")
print(f"  Total chars in all chunks: {total_chars_db}")

cur.close()
conn.close()

# Now let's check the original file
original_file = "rag_indexer/data/markdown/VCR.md"
if os.path.exists(original_file):
    with open(original_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"\nOriginal VCR.md file:")
    print(f"  Length: {len(content)} chars")
    print(f"  Words: {len(content.split())} words")
    print(f"  Lines: {len(content.splitlines())} lines")
