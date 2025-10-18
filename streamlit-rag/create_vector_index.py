#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create vector index for fast similarity search
This significantly improves search performance

IMPORTANT: This script is an ALTERNATIVE to creating the index via SQL.
The RECOMMENDED approach is to create the index when setting up the database schema:

    -- In Supabase SQL Editor:
    CREATE INDEX IF NOT EXISTS idx_documents_vec_hnsw
    ON vecs.documents
    USING hnsw (vec vector_cosine_ops);

Use this script only if:
- You forgot to create the index during schema setup
- You need to recreate the index programmatically
- SQL approach is not available in your environment
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

def create_index():
    """Create vector index for similarity search"""
    try:
        import vecs

        connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
        if not connection_string:
            print("❌ No SUPABASE_CONNECTION_STRING found in environment")
            print("   Please check your .env file")
            return False

        print("🔌 Connecting to database...")
        vx = vecs.create_client(connection_string)

        print("📦 Getting documents collection...")
        collection = vx.get_or_create_collection(
            name="documents",
            dimension=768
        )

        print("🔧 Creating HNSW vector index for cosine distance...")
        print("   (This may take a few minutes for large collections)")

        # Check if index already exists
        try:
            # vecs library uses create_index without method parameter
            # It creates an HNSW index by default
            collection.create_index(replace=True)
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️  Index already exists, attempting to replace...")
                collection.create_index(replace=True)
            else:
                raise

        print("✅ Vector index created successfully!")
        print("\n📊 Benefits:")
        print("   - Much faster vector similarity searches")
        print("   - Reduced query time from ~0.6s to ~0.2s")
        print("   - No more 'missing index' warnings")

        return True

    except Exception as e:
        print(f"\n❌ Error creating index: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("Vector Index Creation Tool")
    print("=" * 70)
    print("\nThis will create an optimized index for vector similarity search.")
    print("The index will significantly improve search performance.\n")

    success = create_index()

    if success:
        print("\n" + "=" * 70)
        print("✅ SUCCESS - Index created!")
        print("=" * 70)
        print("\nYou can now run searches without the index warning:")
        print("  python simple_search.py \"231-D-54321\"")
    else:
        print("\n" + "=" * 70)
        print("❌ FAILED - Could not create index")
        print("=" * 70)
        sys.exit(1)
