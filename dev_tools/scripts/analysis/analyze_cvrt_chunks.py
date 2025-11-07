#!/usr/bin/env python3
"""Analyze CVRT document chunking issue"""

import os
import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
from pathlib import Path

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

registry_id = '982534aa-3848-476b-857f-74768881303e'

with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
    # Get registry info
    cur.execute("""
        SELECT
            id,
            original_filename,
            markdown_file_path,
            uploaded_at
        FROM vecs.document_registry
        WHERE id = %s
    """, (registry_id,))

    doc = cur.fetchone()

    print("\n" + "="*80)
    print("CVRT PASS STATEMENT ANALYSIS")
    print("="*80 + "\n")
    print(f"Registry ID: {doc['id']}")
    print(f"Filename: {doc['original_filename']}")
    print(f"Markdown path: {doc['markdown_file_path']}")
    print()

    # Check markdown file
    md_path = doc['markdown_file_path']
    if md_path and os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print("MARKDOWN FILE:")
        print(f"  Size: {len(content)} chars")
        print(f"  Lines: {content.count(chr(10)) + 1}")
        print(f"  Words: {len(content.split())}")
        print()
        print("Content:")
        print("-" * 80)
        print(content)
        print("-" * 80)
        print()

    # Check JSON file
    json_path = md_path.replace('.md', '.json').replace('markdown', 'json') if md_path else None
    if json_path and os.path.exists(json_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        print("\nJSON FILE (DoclingDocument):")
        print(f"  Path: {json_path}")
        print(f"  Size: {os.path.getsize(json_path)} bytes")

        # Check structure
        if isinstance(json_data, dict):
            print(f"  Keys: {list(json_data.keys())}")

            # Check for tables/pictures
            if 'tables' in json_data:
                print(f"  Tables: {len(json_data.get('tables', []))}")
            if 'pictures' in json_data:
                print(f"  Pictures: {len(json_data.get('pictures', []))}")
            if 'texts' in json_data:
                print(f"  Text elements: {len(json_data.get('texts', []))}")
        print()

    # Get chunk stats
    cur.execute("""
        SELECT
            COUNT(*) as total_chunks,
            AVG(LENGTH(metadata->>'text')) as avg_text_length,
            MIN(LENGTH(metadata->>'text')) as min_text_length,
            MAX(LENGTH(metadata->>'text')) as max_text_length
        FROM vecs.documents
        WHERE registry_id = %s
    """, (registry_id,))

    stats = cur.fetchone()

    print("CHUNK STATISTICS:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Avg text length: {int(stats['avg_text_length']) if stats['avg_text_length'] else 0} chars")
    print(f"  Min text length: {stats['min_text_length']} chars")
    print(f"  Max text length: {stats['max_text_length']} chars")
    print()

    # Sample chunks
    cur.execute("""
        SELECT
            id,
            metadata->>'text' as text,
            LENGTH(metadata->>'text') as text_length
        FROM vecs.documents
        WHERE registry_id = %s
        ORDER BY id
        LIMIT 20
    """, (registry_id,))

    chunks = cur.fetchall()

    print("FIRST 20 CHUNKS:")
    print("-" * 80)
    for i, chunk in enumerate(chunks, 1):
        text_len = chunk['text_length'] if chunk['text_length'] else 0
        text = chunk['text'] if chunk['text'] else 'NULL'
        print(f"\n[Chunk {i}] Length: {text_len}")
        print(f"Text: {text}")

    # Check for duplicates
    cur.execute("""
        SELECT
            metadata->>'text' as text,
            COUNT(*) as count
        FROM vecs.documents
        WHERE registry_id = %s
        GROUP BY metadata->>'text'
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """, (registry_id,))

    duplicates = cur.fetchall()

    if duplicates:
        print("\n" + "="*80)
        print("DUPLICATE CHUNKS (same text appears multiple times):")
        print("="*80)
        total_dups = sum(d['count'] - 1 for d in duplicates)
        print(f"Total duplicate chunks: {total_dups}\n")
        for i, dup in enumerate(duplicates, 1):
            print(f"{i}. Appears {dup['count']} times:")
            print(f"   Text: {dup['text'][:200]}...")
            print()

conn.close()
