#!/usr/bin/env python3
"""Fix the failed record that actually succeeded"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

cur = conn.cursor()

# Fix the record that was marked as failed but actually succeeded
# (it has markdown_file_path and storage_path = raw/processed/...)
cur.execute("""
    UPDATE vecs.document_registry
    SET status = 'processed',
        storage_status = 'processed'
    WHERE storage_status = 'failed'
      AND markdown_file_path IS NOT NULL
      AND storage_path LIKE 'raw/processed/%'
    RETURNING id, original_filename, status, storage_status, storage_path
""")

results = cur.fetchall()
print(f"\nFixed {len(results)} records:")
for row in results:
    print(f"  - {row[1]}")
    print(f"    status: {row[2]}")
    print(f"    storage_status: {row[3]}")
    print(f"    storage_path: {row[4]}")

conn.commit()
conn.close()

print("\nDone!")
