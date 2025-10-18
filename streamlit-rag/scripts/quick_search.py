#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# quick_search.py - Quick search for your specific file

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def quick_search():
    # Your target file
    target_file = "172-MOS Safe Administration of Oxygen IH 17.10.24.doc"
    
    print(f"?? Quick search for: {target_file}")
    print("=" * 80)
    
    # Connect to database
    connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
    if not connection_string:
        print("? No SUPABASE_CONNECTION_STRING found!")
        return
    
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Search strategies
        searches = [
            ("Exact match", "metadata->>'file_name' = %s", target_file),
            ("Case insensitive", "LOWER(metadata->>'file_name') = LOWER(%s)", target_file),
            ("Contains 'Safe Administration'", "metadata->>'file_name' LIKE %s", "%Safe Administration%"),
            ("Contains 'Oxygen'", "metadata->>'file_name' LIKE %s", "%Oxygen%"),
            ("Contains '172-MOS'", "metadata->>'file_name' LIKE %s", "%172-MOS%"),
            ("Contains '.doc'", "metadata->>'file_name' LIKE %s", "%.doc%"),
        ]
        
        for search_name, where_clause, param in searches:
            print(f"\n?? {search_name}:")
            print("-" * 40)
            
            sql = f"""
            SELECT 
                id,
                metadata->>'file_name' as file_name,
                metadata->>'file_path' as file_path,
                metadata->>'chunk_index' as chunk_index,
                LENGTH(metadata->>'text') as content_length
            FROM vecs.documents
            WHERE {where_clause}
            ORDER BY (metadata->>'chunk_index')::int
            """
            
            cur.execute(sql, (param,))
            results = cur.fetchall()
            
            if results:
                print(f"? Found {len(results)} chunks:")
                for result in results:
                    print(f"   ?? {result['file_name']}")
                    print(f"      Chunk: {result['chunk_index']}")
                    print(f"      Content: {result['content_length']} chars")
                    print(f"      ID: {result['id']}")
                    print()
            else:
                print("? No results found")
        
        # List all files with "oxygen" or "MOS" or "172"
        print(f"\n?? All files containing 'oxygen', 'MOS', or '172':")
        print("-" * 60)
        
        sql = """
        SELECT DISTINCT 
            metadata->>'file_name' as file_name,
            COUNT(*) as chunks
        FROM vecs.documents
        WHERE LOWER(metadata->>'file_name') LIKE '%oxygen%'
           OR LOWER(metadata->>'file_name') LIKE '%mos%'
           OR metadata->>'file_name' LIKE '%172%'
        GROUP BY metadata->>'file_name'
        ORDER BY metadata->>'file_name'
        """
        
        cur.execute(sql)
        all_related = cur.fetchall()
        
        if all_related:
            for file_info in all_related:
                print(f"?? {file_info['file_name']} ({file_info['chunks']} chunks)")
        else:
            print("? No related files found")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"? Error: {e}")

if __name__ == "__main__":
    quick_search()