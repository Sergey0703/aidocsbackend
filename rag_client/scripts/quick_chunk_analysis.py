#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# quick_chunk_analysis.py - Quick analysis of files with most chunks

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def quick_chunk_analysis():
    print("?? Quick Chunk Analysis - Top 5 Files with Most Chunks")
    print("=" * 80)
    
    # Connect to database
    connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
    if not connection_string:
        print("? No SUPABASE_CONNECTION_STRING found!")
        return
    
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get top 5 files with most chunks
        print("?? Finding files with most chunks...")
        
        top_files_sql = """
        SELECT 
            metadata->>'file_name' as file_name,
            COUNT(*) as chunk_count,
            SUM(LENGTH(metadata->>'text')) as total_length,
            AVG(LENGTH(metadata->>'text'))::int as avg_chunk_length
        FROM vecs.documents
        WHERE metadata->>'file_name' IS NOT NULL
        GROUP BY metadata->>'file_name'
        ORDER BY chunk_count DESC
        LIMIT 5
        """
        
        cur.execute(top_files_sql)
        top_files = cur.fetchall()
        
        print(f"\n?? Top 5 Files with Most Chunks:")
        print("-" * 80)
        
        for i, file_info in enumerate(top_files, 1):
            print(f"\n{i}. ?? {file_info['file_name']}")
            print(f"   Chunks: {file_info['chunk_count']}")
            print(f"   Total content: {file_info['total_length']:,} characters")
            print(f"   Average chunk: {file_info['avg_chunk_length']:,} characters")
        
        # Show detailed analysis for each file
        print(f"\n" + "=" * 80)
        print("?? DETAILED CONTENT FOR EACH FILE")
        print("=" * 80)
        
        for i, file_info in enumerate(top_files, 1):
            file_name = file_info['file_name']
            
            print(f"\n{'='*10} FILE {i}: {file_name} {'='*10}")
            print(f"Total Chunks: {file_info['chunk_count']}")
            
            # Get all chunks for this file
            chunks_sql = """
            SELECT 
                metadata->>'chunk_index' as chunk_index,
                metadata->>'text' as content,
                LENGTH(metadata->>'text') as content_length
            FROM vecs.documents
            WHERE metadata->>'file_name' = %s
            ORDER BY (metadata->>'chunk_index')::int
            """
            
            cur.execute(chunks_sql, (file_name,))
            chunks = cur.fetchall()
            
            for chunk in chunks:
                chunk_idx = chunk['chunk_index']
                content = chunk['content'] or ""
                content_length = chunk['content_length']
                
                print(f"\n--- CHUNK {chunk_idx} ({content_length:,} characters) ---")
                print(content)
                print(f"--- END CHUNK {chunk_idx} ---\n")
            
            if i < len(top_files):
                print("\n" + "="*60)
                print(f"MOVING TO NEXT FILE...")
                print("="*60)
        
        cur.close()
        conn.close()
        
        print(f"\n? Analysis completed!")
        print("Summary:")
        for i, file_info in enumerate(top_files, 1):
            print(f"  {i}. {file_info['file_name']}: {file_info['chunk_count']} chunks")
        
    except Exception as e:
        print(f"? Error: {e}")

if __name__ == "__main__":
    quick_chunk_analysis()