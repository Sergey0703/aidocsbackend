#!/usr/bin/env python3
"""Fix old document_registry records"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('rag_indexer/.env')

conn_string = os.getenv('SUPABASE_CONNECTION_STRING')
conn = psycopg2.connect(conn_string)

cur = conn.cursor()

# Fix records with status='pending_processing' and storage_status='processed'
# These should have status='processed'
cur.execute("""
    UPDATE vecs.document_registry
    SET status = 'processed'
    WHERE status = 'pending_processing'
      AND storage_status = 'processed'
      AND original_filename IS NOT NULL
    RETURNING id, original_filename, status, storage_status
""")

results = cur.fetchall()
print(f"\nUpdated {len(results)} records:")
for row in results:
    print(f"  - {row[1]}: status -> 'processed'")

# Fix storage_path for records still pointing to raw/pending
cur.execute("""
    UPDATE vecs.document_registry
    SET storage_path = REPLACE(storage_path, 'raw/pending/', 'raw/processed/')
    WHERE storage_path LIKE 'raw/pending/%'
      AND storage_status = 'processed'
    RETURNING id, original_filename, storage_path
""")

results = cur.fetchall()
print(f"\nFixed {len(results)} storage paths:")
for row in results:
    print(f"  - {row[1]}: {row[2]}")

# Delete broken records with all NULL fields
cur.execute("""
    DELETE FROM vecs.document_registry
    WHERE status = 'processed'
      AND storage_status = 'pending'
      AND original_filename IS NULL
      AND raw_file_path IS NULL
      AND storage_path IS NULL
    RETURNING id
""")

results = cur.fetchall()
print(f"\nDeleted {len(results)} broken records")

conn.commit()
conn.close()

print("\n✅ Database cleanup completed!")
