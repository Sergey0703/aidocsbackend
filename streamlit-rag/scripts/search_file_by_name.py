#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scripts/search_file_by_name.py
# Console script to search for files in the database by filename

import os
import sys
import json
import psycopg2
import psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    connection_string = (
        os.getenv("SUPABASE_CONNECTION_STRING") or
        os.getenv("DATABASE_URL") or
        os.getenv("POSTGRES_URL")
    )
    
    if not connection_string:
        print("? Error: No database connection string found!")
        print("   Set SUPABASE_CONNECTION_STRING in your .env file")
        return None
    
    try:
        conn = psycopg2.connect(connection_string)
        return conn
    except Exception as e:
        print(f"? Database connection failed: {e}")
        return None

def search_file_exact(conn, filename):
    """Search for exact filename match"""
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Exact match search
        search_sql = """
        SELECT 
            id,
            metadata,
            (metadata->>'text') as text_content,
            (metadata->>'file_name') as file_name,
            (metadata->>'file_path') as file_path,
            (metadata->>'chunk_index') as chunk_index,
            (metadata->>'total_chunks') as total_chunks
        FROM vecs.documents
        WHERE metadata->>'file_name' = %s
        ORDER BY (metadata->>'chunk_index')::int
        """
        
        cur.execute(search_sql, (filename,))
        results = cur.fetchall()
        
        cur.close()
        return results
        
    except Exception as e:
        print(f"? Search error: {e}")
        return []

def search_file_partial(conn, filename):
    """Search for partial filename match (case insensitive)"""
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Partial match search
        search_sql = """
        SELECT 
            id,
            metadata,
            (metadata->>'text') as text_content,
            (metadata->>'file_name') as file_name,
            (metadata->>'file_path') as file_path,
            (metadata->>'chunk_index') as chunk_index,
            (metadata->>'total_chunks') as total_chunks
        FROM vecs.documents
        WHERE LOWER(metadata->>'file_name') LIKE LOWER(%s)
        ORDER BY metadata->>'file_name', (metadata->>'chunk_index')::int
        """
        
        search_term = f"%{filename}%"
        cur.execute(search_sql, (search_term,))
        results = cur.fetchall()
        
        cur.close()
        return results
        
    except Exception as e:
        print(f"? Partial search error: {e}")
        return []

def search_all_filenames(conn, pattern=None):
    """Get all unique filenames from database"""
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if pattern:
            search_sql = """
            SELECT DISTINCT 
                metadata->>'file_name' as file_name,
                COUNT(*) as chunk_count
            FROM vecs.documents
            WHERE LOWER(metadata->>'file_name') LIKE LOWER(%s)
            GROUP BY metadata->>'file_name'
            ORDER BY metadata->>'file_name'
            """
            search_term = f"%{pattern}%"
            cur.execute(search_sql, (search_term,))
        else:
            search_sql = """
            SELECT DISTINCT 
                metadata->>'file_name' as file_name,
                COUNT(*) as chunk_count
            FROM vecs.documents
            GROUP BY metadata->>'file_name'
            ORDER BY metadata->>'file_name'
            """
            cur.execute(search_sql)
        
        results = cur.fetchall()
        cur.close()
        return results
        
    except Exception as e:
        print(f"? List files error: {e}")
        return []

def print_file_info(results, filename_searched):
    """Print detailed file information"""
    if not results:
        print(f"? No results found for: '{filename_searched}'")
        return
    
    # Group results by filename
    files_dict = {}
    for result in results:
        file_name = result.get('file_name', 'Unknown')
        if file_name not in files_dict:
            files_dict[file_name] = []
        files_dict[file_name].append(result)
    
    print(f"\n?? Search Results for: '{filename_searched}'")
    print("=" * 80)
    
    for file_name, chunks in files_dict.items():
        print(f"\n?? File: {file_name}")
        print(f"   Chunks: {len(chunks)}")
        
        # Get file metadata from first chunk
        first_chunk = chunks[0]
        metadata = first_chunk.get('metadata', {})
        
        print(f"   File Path: {metadata.get('file_path', 'N/A')}")
        print(f"   Total Chunks: {metadata.get('total_chunks', 'N/A')}")
        
        # Show chunk details
        print(f"\n   ?? Chunk Details:")
        for i, chunk in enumerate(chunks):
            chunk_idx = chunk.get('chunk_index', i)
            content = chunk.get('text_content', '')
            content_preview = content[:100].replace('\n', ' ') + "..." if len(content) > 100 else content
            
            print(f"      Chunk {chunk_idx}: {len(content)} chars")
            print(f"      Preview: {content_preview}")
            print(f"      Document ID: {chunk.get('id', 'N/A')}")
            print()

def print_content_full(results, chunk_index=None):
    """Print full content of specific chunk or all chunks"""
    if not results:
        return
    
    if chunk_index is not None:
        # Find specific chunk
        target_chunk = None
        for result in results:
            if str(result.get('chunk_index', '0')) == str(chunk_index):
                target_chunk = result
                break
        
        if target_chunk:
            print(f"\n?? Full Content - Chunk {chunk_index}:")
            print("=" * 80)
            print(target_chunk.get('text_content', 'No content'))
        else:
            print(f"? Chunk {chunk_index} not found")
    else:
        # Print all chunks
        print(f"\n?? Full Content - All Chunks:")
        print("=" * 80)
        
        # Sort by chunk index
        sorted_results = sorted(results, key=lambda x: int(x.get('chunk_index', 0)))
        
        for result in sorted_results:
            chunk_idx = result.get('chunk_index', 0)
            content = result.get('text_content', 'No content')
            
            print(f"\n--- Chunk {chunk_idx} ---")
            print(content)

def interactive_search():
    """Interactive search interface"""
    print("?? File Search Tool")
    print("=" * 50)
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        while True:
            print("\nOptions:")
            print("1. Search by exact filename")
            print("2. Search by partial filename") 
            print("3. List all files")
            print("4. List files by pattern")
            print("5. Exit")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == "1":
                filename = input("Enter exact filename: ").strip()
                if filename:
                    results = search_file_exact(conn, filename)
                    print_file_info(results, filename)
                    
                    if results:
                        show_content = input("\nShow full content? (y/n): ").strip().lower()
                        if show_content == 'y':
                            chunk_choice = input("Enter chunk index (or press Enter for all): ").strip()
                            if chunk_choice:
                                try:
                                    chunk_idx = int(chunk_choice)
                                    print_content_full(results, chunk_idx)
                                except ValueError:
                                    print("Invalid chunk index")
                            else:
                                print_content_full(results)
            
            elif choice == "2":
                filename = input("Enter partial filename: ").strip()
                if filename:
                    results = search_file_partial(conn, filename)
                    print_file_info(results, filename)
                    
                    if results:
                        show_content = input("\nShow full content? (y/n): ").strip().lower()
                        if show_content == 'y':
                            print_content_full(results)
            
            elif choice == "3":
                print("\n?? All Files in Database:")
                print("-" * 50)
                files = search_all_filenames(conn)
                for file_info in files:
                    print(f"?? {file_info['file_name']} ({file_info['chunk_count']} chunks)")
            
            elif choice == "4":
                pattern = input("Enter filename pattern: ").strip()
                if pattern:
                    print(f"\n?? Files matching '{pattern}':")
                    print("-" * 50)
                    files = search_all_filenames(conn, pattern)
                    for file_info in files:
                        print(f"?? {file_info['file_name']} ({file_info['chunk_count']} chunks)")
            
            elif choice == "5":
                print("?? Goodbye!")
                break
            
            else:
                print("? Invalid option")
    
    finally:
        conn.close()

def command_line_search():
    """Command line search interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  python {sys.argv[0]} <filename>")
        print(f"  python {sys.argv[0]} --interactive")
        print(f"  python {sys.argv[0]} --list")
        print("\nExamples:")
        print(f"  python {sys.argv[0]} 'Safe Administration of Oxygen'")
        print(f"  python {sys.argv[0]} '172-MOS Safe Administration of Oxygen IH 17.10.24.doc'")
        return
    
    if sys.argv[1] == "--interactive":
        interactive_search()
        return
    
    if sys.argv[1] == "--list":
        conn = get_db_connection()
        if conn:
            files = search_all_filenames(conn)
            print("\n?? All Files in Database:")
            print("=" * 50)
            for file_info in files:
                print(f"?? {file_info['file_name']} ({file_info['chunk_count']} chunks)")
            conn.close()
        return
    
    filename = sys.argv[1]
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        print(f"?? Searching for: '{filename}'")
        
        # Try exact match first
        results = search_file_exact(conn, filename)
        
        if not results:
            print("No exact match found. Trying partial match...")
            results = search_file_partial(conn, filename)
        
        print_file_info(results, filename)
        
        # Show content if found
        if results and len(sys.argv) > 2 and sys.argv[2] == "--content":
            print_content_full(results)
    
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        command_line_search()
    except KeyboardInterrupt:
        print("\n?? Interrupted by user")
    except Exception as e:
        print(f"? Error: {e}")