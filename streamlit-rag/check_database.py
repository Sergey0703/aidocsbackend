#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick script to check database contents
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

def check_database():
    """Check database contents"""
    try:
        import vecs

        connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
        if not connection_string:
            print("❌ No SUPABASE_CONNECTION_STRING found in environment")
            return

        print("🔌 Connecting to database...")
        vx = vecs.create_client(connection_string)

        # Get collection
        collection = vx.get_or_create_collection(
            name="documents",
            dimension=768
        )

        print(f"✅ Connected to collection: documents")

        # Try to query a few documents
        print("\n📊 Checking collection contents...")

        # Simple test query
        test_results = collection.query(
            data=[0.0] * 768,  # dummy vector
            limit=5,
            include_value=True,
            include_metadata=True
        )

        if test_results:
            print(f"\n✅ Found {len(test_results)} sample documents in database")
            print("\nSample documents:")
            for i, result in enumerate(test_results, 1):
                metadata = result.get('metadata', {}) if isinstance(result, dict) else getattr(result, 'metadata', {})
                file_name = metadata.get('file_name', 'Unknown')
                chunk_index = metadata.get('chunk_index', 'N/A')
                text_preview = metadata.get('text', '')[:100] + "..." if metadata.get('text') else "No text"

                print(f"\n{i}. {file_name}")
                print(f"   Chunk: {chunk_index}")
                print(f"   Preview: {text_preview}")
        else:
            print("\n❌ No documents found in database!")
            print("   The database appears to be empty.")
            print("   You need to run the indexing pipeline first:")
            print("   cd rag_indexer && python pipeline.py")

    except Exception as e:
        print(f"\n❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()
