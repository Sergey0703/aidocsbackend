#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Script: Compare Test2.py vs Streamlit Results for Breeda Daly
This script investigates why the results differ between the two systems
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def investigate_breeda_daly_differences():
    """Investigate why Test2.py and Streamlit show different results"""
    
    print("🔍 INVESTIGATING BREEDA DALY SEARCH DIFFERENCES")
    print("="*70)
    
    # Expected documents from both systems
    test2_docs = [
        "1-BD Dysphagia Kerry SLT Clinic 10.10.23.pdf",
        "1-BDK Food Hygiene SCTV 21.09.23.pdf", 
        "1-BDK Fire Training SCTV 14.09.23.pdf",
        "1-BD Diversity Equality & Inclusion Mod 1 HSELD 28.05.2025.pdf",
        "1-BD Diversity Equality & Inclusion Mod 3 HSELD 28.05.2025.pdf",
        "1-BD Towards Excellence in PCP HSELD 28.05.2025.pdf",
        "1-BD Manual and People Moving and Handling ST 04.04.24.pdf",
        "1-BD Introduction to Sepsis Management for Adults Including Maternity HSELD 24.01.25.pdf",
        "1-BD Diversity Equality & Inclusion Mod 2 HSELD 28.05.2025.pdf",
        "1-BD Children first HSELD 27.05.2025.pdf",
        "1-BDK Safeguarding Adults at Risk of Abuse HSELD 24.10.22.pdf"
    ]
    
    streamlit_docs = [
        "1-BD Manual and People Moving and Handling ST 04.04.24.pdf",
        "1-BD Dysphagia Kerry SLT Clinic 10.10.23.pdf",
        "1-BDK Safeguarding Adults at Risk of Abuse HSELD 24.10.22.pdf",
        "1-BD Towards Excellence in PCP HSELD 28.05.2025.pdf",
        "1-BD Diversity Equality & Inclusion Mod 1 HSELD 28.05.2025.pdf",
        "1-BD AMRIC Hand Hygiene HSELD 10.09.2024.pdf",  # NEW in Streamlit
        "1-BD Introduction to Sepsis Management for Adults Including Maternity HSELD 24.01.25.pdf",
        "1-BD Diversity Equality & Inclusion Mod 3 HSELD 28.05.2025.pdf",
        "1-BD Diversity Equality & Inclusion Mod 2 HSELD 28.05.2025.pdf",
        "1-BD Children first HSELD 27.05.2025.pdf"
    ]
    
    # Find differences
    test2_set = set(test2_docs)
    streamlit_set = set(streamlit_docs)
    
    only_in_test2 = test2_set - streamlit_set
    only_in_streamlit = streamlit_set - test2_set
    common_docs = test2_set & streamlit_set
    
    print(f"📊 COMPARISON RESULTS:")
    print(f"   Test2.py found: {len(test2_docs)} documents")
    print(f"   Streamlit found: {len(streamlit_docs)} documents")
    print(f"   Common documents: {len(common_docs)}")
    print(f"   Only in Test2: {len(only_in_test2)}")
    print(f"   Only in Streamlit: {len(only_in_streamlit)}")
    
    if only_in_test2:
        print(f"\n❌ MISSING in Streamlit (but found in Test2):")
        for doc in only_in_test2:
            print(f"   • {doc}")
    
    if only_in_streamlit:
        print(f"\n➕ EXTRA in Streamlit (not in Test2):")
        for doc in only_in_streamlit:
            print(f"   • {doc}")
    
    # Database investigation
    print(f"\n" + "="*70)
    print("🔍 DATABASE INVESTIGATION")
    print("="*70)
    
    try:
        conn = psycopg2.connect(os.getenv("SUPABASE_CONNECTION_STRING"))
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if missing documents exist in database
        if only_in_test2:
            print(f"\n🔍 Investigating missing documents in Streamlit:")
            for doc in only_in_test2:
                print(f"\n--- Checking: {doc} ---")
                
                cur.execute("""
                SELECT 
                    COUNT(*) as chunk_count,
                    STRING_AGG(DISTINCT metadata->>'text', ' ') as full_text
                FROM vecs.documents 
                WHERE metadata->>'file_name' = %s
                """, (doc,))
                
                result = cur.fetchone()
                if result['chunk_count'] > 0:
                    full_text = result['full_text'] or ""
                    contains_breeda = "breeda daly" in full_text.lower()
                    
                    print(f"   ✅ Found {result['chunk_count']} chunks in database")
                    print(f"   {'✅' if contains_breeda else '❌'} Contains 'Breeda Daly': {contains_breeda}")
                    
                    if contains_breeda:
                        # Find where Breeda Daly appears
                        breeda_pos = full_text.lower().find("breeda daly")
                        context = full_text[max(0, breeda_pos-100):breeda_pos+150]
                        print(f"   📝 Context: ...{context}...")
                else:
                    print(f"   ❌ NOT found in database")
        
        # Check extra documents
        if only_in_streamlit:
            print(f"\n🔍 Investigating extra documents in Streamlit:")
            for doc in only_in_streamlit:
                print(f"\n--- Checking: {doc} ---")
                
                cur.execute("""
                SELECT 
                    COUNT(*) as chunk_count,
                    STRING_AGG(DISTINCT metadata->>'text', ' ') as full_text
                FROM vecs.documents 
                WHERE metadata->>'file_name' = %s
                """, (doc,))
                
                result = cur.fetchone()
                if result['chunk_count'] > 0:
                    full_text = result['full_text'] or ""
                    contains_breeda = "breeda daly" in full_text.lower()
                    
                    print(f"   ✅ Found {result['chunk_count']} chunks in database") 
                    print(f"   {'✅' if contains_breeda else '❌'} Contains 'Breeda Daly': {contains_breeda}")
                    
                    if contains_breeda:
                        breeda_pos = full_text.lower().find("breeda daly")
                        context = full_text[max(0, breeda_pos-100):breeda_pos+150]
                        print(f"   📝 Context: ...{context}...")
                    else:
                        print(f"   ⚠️ Should NOT contain 'Breeda Daly' but was returned by Streamlit")
                        print(f"   🔍 Possible similar terms found")
                else:
                    print(f"   ❌ NOT found in database")
        
        # Overall database check
        print(f"\n🔍 OVERALL DATABASE CHECK:")
        cur.execute("""
        SELECT DISTINCT metadata->>'file_name' as file_name
        FROM vecs.documents 
        WHERE LOWER(metadata->>'text') LIKE '%breeda daly%'
        ORDER BY metadata->>'file_name'
        """)
        
        db_results = cur.fetchall()
        db_files = {result['file_name'] for result in db_results}
        
        print(f"   📊 Database contains {len(db_files)} files with 'Breeda Daly':")
        for file_name in sorted(db_files):
            in_test2 = "✅" if file_name in test2_set else "❌"
            in_streamlit = "✅" if file_name in streamlit_set else "❌"
            print(f"   📄 {file_name}")
            print(f"      Test2: {in_test2} | Streamlit: {in_streamlit}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    # Recommendations
    print(f"\n" + "="*70)
    print("💡 RECOMMENDATIONS")
    print("="*70)
    print("1. 🔧 Check if Streamlit uses different similarity thresholds")
    print("2. 🔧 Verify if fusion algorithm filters out some results") 
    print("3. 🔧 Compare exact search parameters between systems")
    print("4. 🔧 Check if content validation logic differs")
    print("5. 🔧 Investigate why AMRIC Hand Hygiene document appears in Streamlit")

if __name__ == "__main__":
    investigate_breeda_daly_differences()
