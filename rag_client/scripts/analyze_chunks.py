#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scripts/analyze_chunks.py
# Script to analyze files with maximum number of chunks

import os
import sys
import psycopg2
import psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
        return None
    
    try:
        conn = psycopg2.connect(connection_string)
        return conn
    except Exception as e:
        print(f"? Database connection failed: {e}")
        return None

def get_files_with_most_chunks(conn, top_n=5):
    """Get files with the most chunks"""
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        sql = """
        SELECT 
            metadata->>'file_name' as file_name,
            metadata->>'file_path' as file_path,
            COUNT(*) as chunk_count,
            MIN((metadata->>'chunk_index')::int) as min_chunk,
            MAX((metadata->>'chunk_index')::int) as max_chunk,
            SUM(LENGTH(metadata->>'text')) as total_content_length,
            AVG(LENGTH(metadata->>'text'))::int as avg_chunk_length
        FROM vecs.documents
        WHERE metadata->>'file_name' IS NOT NULL
        GROUP BY metadata->>'file_name', metadata->>'file_path'
        ORDER BY chunk_count DESC, total_content_length DESC
        LIMIT %s
        """
        
        cur.execute(sql, (top_n,))
        results = cur.fetchall()
        
        cur.close()
        return results
        
    except Exception as e:
        print(f"? Error getting files with most chunks: {e}")
        return []

def get_file_chunks(conn, file_name):
    """Get all chunks for a specific file"""
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        sql = """
        SELECT 
            id,
            metadata,
            metadata->>'text' as text_content,
            metadata->>'chunk_index' as chunk_index,
            metadata->>'total_chunks' as total_chunks,
            LENGTH(metadata->>'text') as content_length
        FROM vecs.documents
        WHERE metadata->>'file_name' = %s
        ORDER BY (metadata->>'chunk_index')::int
        """
        
        cur.execute(sql, (file_name,))
        results = cur.fetchall()
        
        cur.close()
        return results
        
    except Exception as e:
        print(f"? Error getting chunks for {file_name}: {e}")
        return []

def print_chunk_statistics():
    """Print overall chunk statistics"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Overall statistics
        stats_sql = """
        SELECT 
            COUNT(DISTINCT metadata->>'file_name') as total_files,
            COUNT(*) as total_chunks,
            AVG(chunk_count) as avg_chunks_per_file,
            MAX(chunk_count) as max_chunks_per_file,
            MIN(chunk_count) as min_chunks_per_file
        FROM (
            SELECT 
                metadata->>'file_name' as file_name,
                COUNT(*) as chunk_count
            FROM vecs.documents
            WHERE metadata->>'file_name' IS NOT NULL
            GROUP BY metadata->>'file_name'
        ) file_stats
        """
        
        cur.execute(stats_sql)
        stats = cur.fetchone()
        
        print("?? Chunk Statistics Overview")
        print("=" * 60)
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Chunks: {stats['total_chunks']}")
        print(f"Average Chunks per File: {stats['avg_chunks_per_file']:.1f}")
        print(f"Maximum Chunks per File: {stats['max_chunks_per_file']}")
        print(f"Minimum Chunks per File: {stats['min_chunks_per_file']}")
        
        # Distribution of chunk counts
        dist_sql = """
        SELECT 
            chunk_count,
            COUNT(*) as file_count
        FROM (
            SELECT 
                metadata->>'file_name' as file_name,
                COUNT(*) as chunk_count
            FROM vecs.documents
            WHERE metadata->>'file_name' IS NOT NULL
            GROUP BY metadata->>'file_name'
        ) file_stats
        GROUP BY chunk_count
        ORDER BY chunk_count DESC
        LIMIT 10
        """
        
        cur.execute(dist_sql)
        distribution = cur.fetchall()
        
        print(f"\n?? Top 10 Chunk Count Distribution:")
        print("-" * 40)
        for dist in distribution:
            print(f"  {dist['chunk_count']} chunks: {dist['file_count']} files")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"? Error getting statistics: {e}")

def analyze_top_chunked_files(top_n=5, show_content=True, max_content_per_chunk=2000):
    """Analyze files with most chunks"""
    print(f"?? Analyzing Top {top_n} Files with Most Chunks")
    print("=" * 80)
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Get files with most chunks
        top_files = get_files_with_most_chunks(conn, top_n)
        
        if not top_files:
            print("? No files found")
            return
        
        print(f"\n?? Top {len(top_files)} Files with Most Chunks:")
        print("-" * 60)
        
        for i, file_info in enumerate(top_files, 1):
            print(f"\n{i}. ?? {file_info['file_name']}")
            print(f"   Path: {file_info['file_path'] or 'N/A'}")
            print(f"   Chunks: {file_info['chunk_count']}")
            print(f"   Chunk range: {file_info['min_chunk']} - {file_info['max_chunk']}")
            print(f"   Total content: {file_info['total_content_length']:,} characters")
            print(f"   Average chunk size: {file_info['avg_chunk_length']:,} characters")
        
        if not show_content:
            return
        
        # Show detailed content for each file
        print(f"\n" + "=" * 80)
        print("?? DETAILED CONTENT ANALYSIS")
        print("=" * 80)
        
        for i, file_info in enumerate(top_files, 1):
            file_name = file_info['file_name']
            
            print(f"\n{'='*20} FILE {i}: {file_name} {'='*20}")
            print(f"Total Chunks: {file_info['chunk_count']}")
            print(f"Total Content Length: {file_info['total_content_length']:,} characters")
            
            # Get all chunks for this file
            chunks = get_file_chunks(conn, file_name)
            
            if not chunks:
                print("? No chunks found for this file")
                continue
            
            # Analyze chunk sizes
            chunk_sizes = [chunk['content_length'] for chunk in chunks]
            min_size = min(chunk_sizes)
            max_size = max(chunk_sizes)
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            
            print(f"\n?? Chunk Size Analysis:")
            print(f"   Min chunk size: {min_size:,} chars")
            print(f"   Max chunk size: {max_size:,} chars")
            print(f"   Average chunk size: {avg_size:.0f} chars")
            
            # Show content of each chunk
            print(f"\n?? All Chunks Content:")
            print("-" * 60)
            
            for chunk in chunks:
                chunk_idx = chunk['chunk_index']
                content = chunk['text_content'] or "No content"
                content_length = chunk['content_length']
                
                print(f"\n--- CHUNK {chunk_idx} ({content_length:,} chars) ---")
                
                if len(content) > max_content_per_chunk:
                    # Show beginning and end if content is too long
                    preview_size = max_content_per_chunk // 2
                    beginning = content[:preview_size]
                    ending = content[-preview_size:]
                    
                    print(beginning)
                    print(f"\n... [TRUNCATED - {len(content) - max_content_per_chunk:,} characters omitted] ...\n")
                    print(ending)
                else:
                    print(content)
                
                print(f"\n--- END CHUNK {chunk_idx} ---")
            
            # Ask if user wants to continue to next file
            if i < len(top_files):
                try:
                    continue_choice = input(f"\nPress Enter to continue to next file, or 'q' to quit: ").strip().lower()
                    if continue_choice == 'q':
                        break
                except KeyboardInterrupt:
                    print("\n?? Interrupted by user")
                    break
        
        conn.close()
        
    except Exception as e:
        print(f"? Error during analysis: {e}")

def interactive_chunk_analysis():
    """Interactive chunk analysis"""
    print("?? Interactive Chunk Analysis Tool")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Show chunk statistics overview")
        print("2. Analyze top 5 files with most chunks")
        print("3. Analyze top N files with most chunks")
        print("4. Analyze specific file by name")
        print("5. Find files with chunks over X characters")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            print_chunk_statistics()
        
        elif choice == "2":
            show_content = input("Show full content? (y/n): ").strip().lower() == 'y'
            if show_content:
                max_chars = input("Max characters per chunk to display (default 2000): ").strip()
                try:
                    max_chars = int(max_chars) if max_chars else 2000
                except ValueError:
                    max_chars = 2000
            else:
                max_chars = 0
            analyze_top_chunked_files(5, show_content, max_chars)
        
        elif choice == "3":
            try:
                n = int(input("Enter number of top files to analyze: ").strip())
                show_content = input("Show full content? (y/n): ").strip().lower() == 'y'
                if show_content:
                    max_chars = input("Max characters per chunk to display (default 2000): ").strip()
                    try:
                        max_chars = int(max_chars) if max_chars else 2000
                    except ValueError:
                        max_chars = 2000
                else:
                    max_chars = 0
                analyze_top_chunked_files(n, show_content, max_chars)
            except ValueError:
                print("? Invalid number")
        
        elif choice == "4":
            filename = input("Enter filename: ").strip()
            if filename:
                conn = get_db_connection()
                if conn:
                    chunks = get_file_chunks(conn, filename)
                    if chunks:
                        print(f"\n?? File: {filename}")
                        print(f"Chunks: {len(chunks)}")
                        for chunk in chunks:
                            print(f"\nChunk {chunk['chunk_index']}:")
                            print(f"Length: {chunk['content_length']} chars")
                            print("Content:")
                            print("-" * 40)
                            print(chunk['text_content'][:1000] + "..." if len(chunk['text_content']) > 1000 else chunk['text_content'])
                    else:
                        print(f"? File '{filename}' not found")
                    conn.close()
        
        elif choice == "5":
            try:
                min_chars = int(input("Enter minimum chunk size in characters: ").strip())
                conn = get_db_connection()
                if conn:
                    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    sql = """
                    SELECT 
                        metadata->>'file_name' as file_name,
                        metadata->>'chunk_index' as chunk_index,
                        LENGTH(metadata->>'text') as content_length
                    FROM vecs.documents
                    WHERE LENGTH(metadata->>'text') >= %s
                    ORDER BY content_length DESC
                    LIMIT 20
                    """
                    cur.execute(sql, (min_chars,))
                    results = cur.fetchall()
                    
                    print(f"\n?? Chunks with ={min_chars:,} characters:")
                    for result in results:
                        print(f"?? {result['file_name']} - Chunk {result['chunk_index']}: {result['content_length']:,} chars")
                    
                    cur.close()
                    conn.close()
            except ValueError:
                print("? Invalid number")
        
        elif choice == "6":
            print("?? Goodbye!")
            break
        
        else:
            print("? Invalid option")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            interactive_chunk_analysis()
        elif sys.argv[1] == "--stats":
            print_chunk_statistics()
        elif sys.argv[1] == "--top":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            show_content = "--content" in sys.argv
            max_chars = 2000
            if "--max-chars" in sys.argv:
                try:
                    idx = sys.argv.index("--max-chars")
                    max_chars = int(sys.argv[idx + 1])
                except (IndexError, ValueError):
                    max_chars = 2000
            analyze_top_chunked_files(n, show_content, max_chars)
        else:
            print("Usage:")
            print(f"  python {sys.argv[0]} --interactive")
            print(f"  python {sys.argv[0]} --stats")
            print(f"  python {sys.argv[0]} --top [N] [--content] [--max-chars N]")
    else:
        # Default: show top 5 with content
        analyze_top_chunked_files(5, True, 2000)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n?? Interrupted by user")
    except Exception as e:
        print(f"? Error: {e}")