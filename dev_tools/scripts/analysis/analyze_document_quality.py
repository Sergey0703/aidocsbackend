#!/usr/bin/env python3
"""
Analyze document quality - compare original PDFs with vectorized chunks
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

# Load environment
load_dotenv()

def get_db_connection():
    """Get database connection"""
    connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
    if not connection_string:
        print("[ERR] Error: No SUPABASE_CONNECTION_STRING found!")
        return None

    try:
        conn = psycopg2.connect(connection_string)
        return conn
    except Exception as e:
        print(f"[ERR] Database connection failed: {e}")
        return None

def analyze_document(original_filename):
    """
    Analyze how well a document was processed

    Args:
        original_filename: Name of the original file (e.g., 'Vehicle Registration Certificate.pdf')
    """
    print(f"\n{'='*80}")
    print(f"📄 ANALYZING: {original_filename}")
    print(f"{'='*80}")

    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Find registry entry
        cur.execute("""
            SELECT
                id,
                original_filename,
                document_type,
                status,
                markdown_storage_path,
                json_storage_path,
                extracted_data
            FROM vecs.document_registry
            WHERE original_filename = %s
            LIMIT 1
        """, (original_filename,))

        registry = cur.fetchone()

        if not registry:
            print(f"[ERR] No registry entry found for '{original_filename}'")
            print("   Available documents:")
            cur.execute("""
                SELECT DISTINCT original_filename
                FROM vecs.document_registry
                ORDER BY original_filename
            """)
            for row in cur.fetchall():
                print(f"      • {row['original_filename']}")
            return

        print(f"\n📋 REGISTRY INFO:")
        print(f"   ID: {registry['id']}")
        print(f"   Status: {registry['status']}")
        print(f"   Document Type: {registry['document_type']}")
        print(f"   Extracted Data: {registry['extracted_data']}")

        # Get chunks
        cur.execute("""
            SELECT
                id,
                metadata->>'text' as text_content,
                metadata->>'chunk_index' as chunk_index,
                metadata->>'total_chunks' as total_chunks,
                LENGTH(metadata->>'text') as content_length,
                metadata->>'file_name' as file_name,
                metadata->>'registry_id' as registry_id
            FROM vecs.documents
            WHERE metadata->>'registry_id' = %s
            ORDER BY (metadata->>'chunk_index')::int
        """, (str(registry['id']),))

        chunks = cur.fetchall()

        if not chunks:
            print(f"\n[ERR] No chunks found with registry_id = {registry['id']}")
            return

        print(f"\n[OK] CHUNKS FOUND: {len(chunks)}")
        print(f"   Total chunks: {chunks[0]['total_chunks'] if chunks else 'N/A'}")

        # Chunk statistics
        total_chars = sum(c['content_length'] for c in chunks)
        avg_chars = total_chars / len(chunks)
        min_chars = min(c['content_length'] for c in chunks)
        max_chars = max(c['content_length'] for c in chunks)

        print(f"\n📊 CHUNK STATISTICS:")
        print(f"   Total characters: {total_chars:,}")
        print(f"   Average chunk size: {avg_chars:.0f} chars")
        print(f"   Min chunk size: {min_chars:,} chars")
        print(f"   Max chunk size: {max_chars:,} chars")

        # Show each chunk
        print(f"\n📝 CHUNK CONTENTS:")
        print(f"{'='*80}")

        for chunk in chunks:
            idx = chunk['chunk_index']
            content = chunk['text_content'] or ""
            length = chunk['content_length']

            print(f"\n--- CHUNK {idx} ({length:,} chars) ---")
            print(content)
            print(f"--- END CHUNK {idx} ---\n")

        cur.close()
        conn.close()

        print(f"\n{'='*80}")
        print(f"[OK] Analysis complete for: {original_filename}")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"[ERR] Error during analysis: {e}")
        import traceback
        traceback.print_exc()

def list_all_documents():
    """List all available documents"""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT
                original_filename,
                document_type,
                status,
                COUNT(d.id) as chunk_count
            FROM vecs.document_registry dr
            LEFT JOIN vecs.documents d ON d.metadata->>'registry_id' = dr.id::text
            GROUP BY dr.id, original_filename, document_type, status
            ORDER BY original_filename
        """)

        docs = cur.fetchall()

        print(f"\n{'='*80}")
        print(f"📚 ALL DOCUMENTS IN SYSTEM:")
        print(f"{'='*80}")

        for i, doc in enumerate(docs, 1):
            print(f"\n{i}. {doc['original_filename']}")
            print(f"   Type: {doc['document_type'] or 'N/A'}")
            print(f"   Status: {doc['status']}")
            print(f"   Chunks: {doc['chunk_count']}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[ERR] Error listing documents: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_all_documents()
        else:
            # Analyze specific document
            filename = " ".join(sys.argv[1:])
            analyze_document(filename)
    else:
        print("Usage:")
        print("  python analyze_document_quality.py --list")
        print("  python analyze_document_quality.py <filename>")
        print("\nExamples:")
        print("  python analyze_document_quality.py 'Vehicle Registration Certificate.pdf'")
        print("  python analyze_document_quality.py 'VCR2.docx'")
