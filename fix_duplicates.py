#!/usr/bin/env python3
"""Fix duplicate registry entries and chunks"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

cur = conn.cursor()

# Delete the duplicate registry entry created by markdown_loader
# (the one WITHOUT original_filename)
cur.execute("""
    DELETE FROM vecs.document_registry
    WHERE id = 'b5242bb3-2d88-4ea8-bbb1-6adba2943e1c'
    RETURNING id, markdown_file_path
""")

result = cur.fetchone()
if result:
    print(f"\nDeleted duplicate registry entry: {result[0]}")
    print(f"  Path: {result[1]}")

# Check if there are orphaned chunks
cur.execute("""
    SELECT COUNT(*) FROM vecs.documents
    WHERE registry_id = 'b5242bb3-2d88-4ea8-bbb1-6adba2943e1c'
""")

chunk_count = cur.fetchone()[0]
if chunk_count > 0:
    print(f"  Also deleted {chunk_count} chunks (CASCADE)")

conn.commit()

print("\n# Remaining records for VCR.docx:")
cur.execute("""
    SELECT id, original_filename, status, storage_status
    FROM vecs.document_registry
    WHERE original_filename = 'VCR.docx'
       OR markdown_file_path LIKE '%1761317407_VCR%'
""")

for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]} (status={row[2]}, storage_status={row[3]})")

conn.close()

print("\nDone!")
