#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate why documents are missing - check their actual similarity scores
"""

import os
import time
import logging
import psycopg2
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.retrievers import VectorIndexRetriever

load_dotenv()

# Configuration
CONFIG = {
    "connection_string": os.getenv("SUPABASE_CONNECTION_STRING"),
    "embed_model": "nomic-embed-text",
    "embed_dim": 768,
    "ollama_url": "http://localhost:11434"
}

def get_vector_components():
    """Initialize vector components"""
    try:
        vector_store = SupabaseVectorStore(
            postgres_connection_string=CONFIG["connection_string"],
            collection_name="documents",
            dimension=CONFIG["embed_dim"],
        )
        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        embed_model = OllamaEmbedding(
            model_name=CONFIG["embed_model"], 
            base_url=CONFIG["ollama_url"]
        )
        
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            embed_model=embed_model
        )
        
        return index, embed_model
    except Exception as e:
        print(f"? Error initializing components: {e}")
        return None, None

def investigate_similarity_scores():
    """Check actual similarity scores for all Breeda Daly documents"""
    
    print("?? INVESTIGATING SIMILARITY SCORES FOR ALL BREEDA DALY DOCUMENTS")
    print("="*80)
    
    # Initialize vector search
    index, embed_model = get_vector_components()
    if not index or not embed_model:
        return
    
    # Get all documents from database that contain Breeda Daly
    try:
        conn = psycopg2.connect(CONFIG["connection_string"])
        cur = conn.cursor()
        
        cur.execute("""
        SELECT DISTINCT metadata->>'file_name' as file_name
        FROM vecs.documents 
        WHERE LOWER(metadata->>'text') LIKE '%breeda daly%'
        ORDER BY metadata->>'file_name'
        """)
        
        all_breeda_files = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        print(f"?? Found {len(all_breeda_files)} files in database with 'Breeda Daly'")
        
    except Exception as e:
        print(f"? Database error: {e}")
        return
    
    # Perform vector search with maximum allowed top_k (1000 is the limit!)
    print(f"\n?? Performing vector search with maximum top_k=1000...")
    print("??  Note: Supabase/vecs has a 1000 result limit - this might explain missing documents!")
    
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=1000,  # Maximum allowed by Supabase/vecs
        embed_model=embed_model
    )
    
    nodes = retriever.retrieve("Breeda Daly")
    print(f"?? Retrieved {len(nodes)} total candidate nodes from vector search")
    
    # Analyze similarity scores for all Breeda Daly documents
    file_scores = {}
    found_files = set()
    
    for node in nodes:
        try:
            # Get filename from metadata
            file_name = 'Unknown'
            if hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                file_name = node.node.metadata.get('file_name', 'Unknown')
            elif hasattr(node, 'metadata'):
                file_name = node.metadata.get('file_name', 'Unknown')
            
            # Get content
            content = node.get_content() if hasattr(node, 'get_content') else str(node)
            
            # Check if this file contains Breeda Daly
            if file_name in all_breeda_files and "breeda daly" in content.lower():
                similarity_score = getattr(node, 'score', 0.0)
                
                if file_name not in file_scores or similarity_score > file_scores[file_name]:
                    file_scores[file_name] = similarity_score
                
                found_files.add(file_name)
                
        except Exception as e:
            print(f"?? Error processing node: {e}")
            continue
    
    # Report results
    print(f"\n?? SIMILARITY SCORE ANALYSIS:")
    print("="*80)
    
    # Sort by similarity score
    sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Categories
    high_scores = []    # >= 0.35
    medium_scores = []  # 0.20 - 0.34
    low_scores = []     # < 0.20
    missing_files = []  # Not found in vector search
    
    for file_name, score in sorted_files:
        if score >= 0.35:
            high_scores.append((file_name, score))
        elif score >= 0.20:
            medium_scores.append((file_name, score))
        else:
            low_scores.append((file_name, score))
    
    # Files not found in vector search
    for file_name in all_breeda_files:
        if file_name not in found_files:
            missing_files.append(file_name)
    
    # Display results
    print(f"? HIGH SCORES (=0.35) - {len(high_scores)} files:")
    print("   (These should appear in test2.py results)")
    for file_name, score in high_scores:
        test2_status = "?" if file_name in [
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
        ] else "?"
        
        print(f"   {score:.4f} | {test2_status} | {file_name}")
    
    print(f"\n?? MEDIUM SCORES (0.20-0.34) - {len(medium_scores)} files:")
    print("   (These are filtered out by 0.35 threshold)")
    for file_name, score in medium_scores:
        print(f"   {score:.4f} | ?? | {file_name}")
    
    print(f"\n? LOW SCORES (<0.20) - {len(low_scores)} files:")
    print("   (These have very low similarity)")
    for file_name, score in low_scores:
        print(f"   {score:.4f} | ?? | {file_name}")
    
    if missing_files:
        print(f"\n?? NOT FOUND IN VECTOR SEARCH - {len(missing_files)} files:")
        print("   (These might have embedding issues)")
        for file_name in missing_files:
            print(f"   N/A    | ?? | {file_name}")
    
    # Summary
    print(f"\n?? SUMMARY:")
    print(f"   Database total: {len(all_breeda_files)} files")
    print(f"   Found in vector search: {len(found_files)} files")
    print(f"   High scores (=0.35): {len(high_scores)} files")
    print(f"   Would be filtered by test2.py: {len(medium_scores) + len(low_scores) + len(missing_files)} files")
    
    # ?? CRITICAL: Check if we're hitting the 1000 limit
    if len(nodes) == 1000:
        print(f"\n?? CRITICAL DISCOVERY: We hit the 1000 result limit!")
        print(f"   This means some documents might be missing because they rank beyond position 1000")
        print(f"   Database has 15232 documents, but we can only retrieve top 1000")
        print(f"   Missing documents might have lower similarity scores and get cut off")
    
    # Analysis of missing documents
    if missing_files:
        print(f"\n?? MISSING DOCUMENTS ANALYSIS:")
        print(f"   These {len(missing_files)} files contain 'Breeda Daly' but aren't in top 1000 vector results")
        print(f"   They likely have very low embedding similarity to 'Breeda Daly' query")
        print(f"   Possible reasons:")
        print(f"   - 'Breeda Daly' appears only as signature/name reference")
        print(f"   - Different context (not training-related)")
        print(f"   - Poor text extraction quality")
    
    # Specific investigation for the problematic files
    print(f"\n?? SPECIFIC INVESTIGATION:")
    print("-" * 60)
    
    problematic_files = [
        "1-BDK Food Hygiene SCTV 21.09.23.pdf",
        "1-BDK Fire Training SCTV 14.09.23.pdf", 
        "1-BD AMRIC Hand Hygiene HSELD 10.09.2024.pdf"
    ]
    
    for file_name in problematic_files:
        if file_name in file_scores:
            score = file_scores[file_name]
            status = "? Above threshold" if score >= 0.35 else "? Below threshold"
            print(f"?? {file_name}")
            print(f"   Similarity: {score:.4f} | {status}")
            
            # Additional analysis
            if file_name == "1-BD AMRIC Hand Hygiene HSELD 10.09.2024.pdf":
                print(f"   ?? This file appears in Streamlit but not test2.py")
                if score < 0.35:
                    print(f"   ?? Streamlit might use lower threshold or different filtering")
            elif file_name in ["1-BDK Food Hygiene SCTV 21.09.23.pdf", "1-BDK Fire Training SCTV 14.09.23.pdf"]:
                print(f"   ?? This file appears in test2.py but not Streamlit")
                if score >= 0.35:
                    print(f"   ?? Streamlit fusion might be filtering this out")
        else:
            print(f"?? {file_name}: NOT FOUND in vector search")

if __name__ == "__main__":
    investigate_similarity_scores()