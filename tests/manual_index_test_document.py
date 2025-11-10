#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual indexing script for test document.

This script bypasses the API and directly indexes the test document
using the same backend components that the API uses.

Usage:
    python tests/manual_index_test_document.py
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent
env_path = project_root / "rag_indexer" / ".env"
load_dotenv(env_path)

# Add backend to path
sys.path.insert(0, str(project_root / "rag_indexer"))

# Test document details
TEST_REGISTRY_ID = "81a879fa-d6e5-4d49-b33d-692aa3a2b1de"
TEST_FILENAME = "Vehicle_Service_Report_Toyota_Camry_2023.pdf"
MARKDOWN_STORAGE_PATH = "markdown/processed/Vehicle_Service_Report_Toyota_Camry_2023.md"
JSON_STORAGE_PATH = "json/processed/Vehicle_Service_Report_Toyota_Camry_2023.json"


def main():
    """Manually index the test document."""
    print("=" * 70)
    print("MANUAL INDEXING - Test Document")
    print("=" * 70)
    print(f"Registry ID: {TEST_REGISTRY_ID}")
    print(f"Filename: {TEST_FILENAME}")
    print()

    # Step 1: Download markdown and JSON from Storage
    print("Step 1: Downloading files from Supabase Storage...")
    print("-" * 70)

    from storage.storage_manager import SupabaseStorageManager
    import tempfile
    import shutil

    storage_manager = SupabaseStorageManager()
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Download markdown
        print(f"Downloading: {MARKDOWN_STORAGE_PATH}")
        md_temp = storage_manager.download_to_temp(MARKDOWN_STORAGE_PATH)
        md_dest = temp_dir / "Vehicle_Service_Report_Toyota_Camry_2023.md"
        shutil.copy(md_temp, md_dest)
        print(f"  Saved to: {md_dest}")

        # Download JSON
        print(f"Downloading: {JSON_STORAGE_PATH}")
        json_temp = storage_manager.download_to_temp(JSON_STORAGE_PATH)
        json_dest = temp_dir / "Vehicle_Service_Report_Toyota_Camry_2023.json"
        shutil.copy(json_temp, json_dest)
        print(f"  Saved to: {json_dest}")

        print(f"\n[OK] Files downloaded to: {temp_dir}")

        # Step 2: Load documents using markdown_loader
        print("\nStep 2: Loading documents...")
        print("-" * 70)

        from llama_index.core import Document

        # Read markdown
        with open(md_dest, 'r', encoding='utf-8') as f:
            text = f.read()

        # Create document with metadata
        doc = Document(
            text=text,
            metadata={
                'file_name': TEST_FILENAME,
                'file_path': str(md_dest),
                'registry_id': TEST_REGISTRY_ID,
                'markdown_file_path': str(md_dest),
                'json_file_path': str(json_dest),
            }
        )

        print(f"[OK] Document loaded: {len(text)} chars")

        # Step 3: Chunk using HybridChunker
        print("\nStep 3: Chunking with HybridChunker...")
        print("-" * 70)

        from chunking_vectors.config import Config

        config = Config()
        print(f"USE_HYBRID_CHUNKING: {config.USE_HYBRID_CHUNKING}")
        print(f"CHUNK_SIZE: {config.CHUNK_SIZE}")
        print(f"CHUNK_OVERLAP: {config.CHUNK_OVERLAP}")

        if config.USE_HYBRID_CHUNKING:
            from chunking_vectors.hybrid_chunker import create_hybrid_chunker

            # Update config to use temp directory for JSON
            config.JSON_OUTPUT_DIR = str(temp_dir)

            chunker = create_hybrid_chunker(config)

            print(f"[OK] HybridChunker created")

            # Chunk the document
            nodes = chunker.process_documents([doc])

            print(f"\n[OK] Chunking complete: {len(nodes)} chunks created")

            # Analyze chunks
            print("\nChunk Analysis:")
            print("-" * 70)

            for idx, node in enumerate(nodes[:5], 1):  # Show first 5
                content = node.get_content()
                has_table = '|' in content and ('---' in content or '|-' in content)
                has_heading = '##' in content

                print(f"\nChunk {idx}/{len(nodes)} ({len(content)} chars)")
                if has_table:
                    print("  [TABLE] Contains table")
                if has_heading:
                    print("  [HEADING] Contains headings")

                # Preview
                preview = content[:200].replace('\n', ' ')
                print(f"  Preview: {preview}...")

            if len(nodes) > 5:
                print(f"\n... and {len(nodes) - 5} more chunks")

            # Check table integrity
            print("\n" + "=" * 70)
            print("TABLE INTEGRITY CHECK:")
            print("=" * 70)

            table_chunks = []
            for idx, node in enumerate(nodes, 1):
                content = node.get_content()
                if 'Service Type' in content and '|' in content:
                    table_chunks.append((idx, node))

            if table_chunks:
                print(f"\nFound {len(table_chunks)} chunks with service history table")

                for chunk_idx, node in table_chunks:
                    content = node.get_content()
                    lines = content.split('\n')
                    table_lines = [l for l in lines if '|' in l and l.strip()]

                    print(f"\nChunk {chunk_idx}:")
                    print(f"  Table lines: {len(table_lines)}")

                    # Check for "TOTAL" row
                    has_total = any('TOTAL' in line for line in table_lines)
                    print(f"  Has TOTAL row: {has_total}")

                    # Check for incomplete rows
                    pipe_counts = [l.count('|') for l in table_lines if l.strip() and not '---' in l]
                    if pipe_counts:
                        unique_counts = set(pipe_counts)
                        if len(unique_counts) > 1:
                            print(f"  [WARN] Inconsistent column counts: {unique_counts}")
                        else:
                            print(f"  [OK] Consistent columns: {pipe_counts[0]} pipes")
            else:
                print("[WARN] No service history table found in any chunk")

        else:
            print("[ERROR] USE_HYBRID_CHUNKING is False - cannot test HybridChunker")
            return

        # Step 4: Generate embeddings and save to database
        print("\n" + "=" * 70)
        print("Step 4: Generating embeddings and saving to database...")
        print("-" * 70)

        response = input("\nProceed with database insertion? (yes/no): ").strip().lower()

        if response == 'yes':
            from chunking_vectors.embedding_processor import create_embedding_processor
            from chunking_vectors.database_manager import DatabaseManager

            # Get connection string
            connection_string = os.getenv('SUPABASE_CONNECTION_STRING')

            # Create embedding processor
            embed_processor = create_embedding_processor()

            print("\nGenerating embeddings...")
            nodes_with_embeddings = embed_processor.process_nodes(nodes)

            print(f"[OK] Embeddings generated for {len(nodes_with_embeddings)} chunks")

            # Save to database
            print("\nSaving to database...")
            db_manager = DatabaseManager(connection_string=connection_string)

            # Delete existing chunks for this document first
            print(f"Deleting existing chunks for registry_id: {TEST_REGISTRY_ID}")
            # TODO: Add deletion logic if needed

            # Save nodes
            db_manager.save_nodes(nodes_with_embeddings)

            print(f"[OK] {len(nodes_with_embeddings)} chunks saved to database")

            # Update document_registry status
            import psycopg2
            conn = psycopg2.connect(connection_string)
            cur = conn.cursor()
            cur.execute(
                "UPDATE vecs.document_registry SET status = 'processed', updated_at = NOW() WHERE id = %s",
                (TEST_REGISTRY_ID,)
            )
            conn.commit()
            cur.close()
            conn.close()

            print("[OK] Document registry status updated to 'processed'")

            print("\n" + "=" * 70)
            print("[SUCCESS] Manual indexing completed!")
            print("=" * 70)
            print(f"Total chunks: {len(nodes_with_embeddings)}")
            print(f"Registry ID: {TEST_REGISTRY_ID}")
            print(f"\nYou can now search for this document via API or frontend.")

        else:
            print("\n[SKIP] Database insertion skipped")
            print("\nChunking analysis complete. No changes made to database.")

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\nTemp directory cleaned up: {temp_dir}")


if __name__ == "__main__":
    main()
