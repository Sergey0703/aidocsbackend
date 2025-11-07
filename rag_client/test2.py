#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test2.py - Hybrid Search Theory Test
Testing if combining vector + direct database search finds all 20 Breeda Daly documents
"""

import os
import time
import logging
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "connection_string": os.getenv("SUPABASE_CONNECTION_STRING"),
    "embed_model": "nomic-embed-text",
    "embed_dim": 768,
    "ollama_url": "http://localhost:11434",
    "vector_threshold": 0.30,  # Lowered from 0.35
    "max_top_k": 1000
}

class HybridResult:
    """Simple class to hold search results"""
    def __init__(self, filename, content, similarity_score, source_method, metadata=None):
        self.filename = filename
        self.content = content
        self.similarity_score = similarity_score
        self.source_method = source_method
        self.metadata = metadata or {}

def get_vector_components():
    """Initialize vector components"""
    logger.info("?? Initializing vector components...")
    
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
        
        logger.info(f"? Vector components initialized")
        return index, embed_model
        
    except Exception as e:
        logger.error(f"? Error initializing vector components: {e}")
        return None, None

def vector_search(query, threshold=None):
    """Original vector search method"""
    threshold = threshold or CONFIG["vector_threshold"]
    
    logger.info(f"?? Vector search: '{query}' (threshold: {threshold})")
    
    try:
        index, embed_model = get_vector_components()
        if not index or not embed_model:
            return []
        
        # Create retriever with max top_k
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=CONFIG["max_top_k"],
            embed_model=embed_model
        )
        
        # Apply similarity filter
        similarity_filter = SimilarityPostprocessor(similarity_cutoff=threshold)
        
        # Execute search
        nodes = retriever.retrieve(query)
        filtered_nodes = similarity_filter.postprocess_nodes(nodes)
        
        logger.info(f"   Vector: {len(nodes)} candidates ? {len(filtered_nodes)} after similarity filter")
        
        # Convert to our result format
        results = []
        for node in filtered_nodes:
            try:
                content = node.get_content()
                
                # Only include if contains the search term
                if query.lower() in content.lower():
                    # Extract metadata
                    file_name = 'Unknown'
                    if hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                        file_name = node.node.metadata.get('file_name', 'Unknown')
                    elif hasattr(node, 'metadata'):
                        file_name = node.metadata.get('file_name', 'Unknown')
                    
                    similarity_score = getattr(node, 'score', 0.0)
                    
                    results.append(HybridResult(
                        filename=file_name,
                        content=content,
                        similarity_score=similarity_score,
                        source_method="vector_search",
                        metadata={"original_node": node}
                    ))
                    
            except Exception as e:
                logger.warning(f"?? Error processing vector node: {e}")
                continue
        
        logger.info(f"   Vector: {len(results)} final results after content filter")
        return results
        
    except Exception as e:
        logger.error(f"? Vector search failed: {e}")
        return []

def direct_database_search(query):
    """NEW: Direct database search for exact matches"""
    logger.info(f"?? Direct DB search: '{query}'")
    
    try:
        conn = psycopg2.connect(CONFIG["connection_string"])
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Search for exact matches in document content
        search_sql = """
        SELECT 
            metadata->>'file_name' as file_name,
            metadata->>'text' as text_content,
            metadata->>'chunk_index' as chunk_index,
            id
        FROM vecs.documents
        WHERE LOWER(metadata->>'text') LIKE LOWER(%s)
        AND metadata->>'file_name' IS NOT NULL
        ORDER BY metadata->>'file_name', (metadata->>'chunk_index')::int
        """
        
        search_term = f"%{query}%"
        cur.execute(search_sql, (search_term,))
        rows = cur.fetchall()
        
        logger.info(f"   Database: Found {len(rows)} matching chunks")
        
        # Group by filename and take best chunk per file
        file_results = {}
        for row in rows:
            file_name = row['file_name']
            content = row['text_content'] or ""
            
            # Calculate a simple relevance score based on query frequency
            query_count = content.lower().count(query.lower())
            relevance_score = min(0.95, 0.5 + (query_count * 0.1))  # 0.5 base + 0.1 per occurrence
            
            if file_name not in file_results or relevance_score > file_results[file_name].similarity_score:
                file_results[file_name] = HybridResult(
                    filename=file_name,
                    content=content,
                    similarity_score=relevance_score,
                    source_method="database_exact",
                    metadata={
                        "chunk_index": row['chunk_index'],
                        "document_id": row['id'],
                        "query_occurrences": query_count
                    }
                )
        
        results = list(file_results.values())
        logger.info(f"   Database: {len(results)} unique files found")
        
        cur.close()
        conn.close()
        
        return results
        
    except Exception as e:
        logger.error(f"? Database search failed: {e}")
        return []

def hybrid_search(query):
    """NEW: Hybrid search combining vector + database"""
    logger.info(f"?? HYBRID SEARCH for: '{query}'")
    start_time = time.time()
    
    # Run both searches in parallel (conceptually)
    vector_results = vector_search(query)
    database_results = direct_database_search(query)
    
    logger.info(f"?? Search Results:")
    logger.info(f"   Vector search: {len(vector_results)} results")
    logger.info(f"   Database search: {len(database_results)} results")
    
    # Combine and deduplicate results
    all_results = {}  # filename -> best result
    
    # Add vector results
    for result in vector_results:
        filename = result.filename
        if filename not in all_results or result.similarity_score > all_results[filename].similarity_score:
            all_results[filename] = result
    
    # Add database results (merge or replace)
    for result in database_results:
        filename = result.filename
        if filename not in all_results:
            # New file found by database search
            all_results[filename] = result
            result.metadata["found_by"] = "database_only"
        else:
            # File found by both methods - keep the better one but note both found it
            existing = all_results[filename]
            if result.similarity_score > existing.similarity_score:
                all_results[filename] = result
                result.metadata["found_by"] = "database_better"
            else:
                existing.metadata["found_by"] = "vector_better"
            existing.metadata["found_by_both"] = True
    
    # Sort by similarity score
    final_results = sorted(all_results.values(), key=lambda x: x.similarity_score, reverse=True)
    
    total_time = time.time() - start_time
    
    logger.info(f"? HYBRID RESULTS:")
    logger.info(f"   Total unique files: {len(final_results)}")
    logger.info(f"   Search time: {total_time:.3f}s")
    
    return final_results

def compare_searches(query):
    """Compare original vs hybrid search"""
    print(f"\n" + "="*80)
    print(f"?? COMPARISON TEST: '{query}'")
    print("="*80)
    
    # Test original approach
    print(f"\n1?? ORIGINAL VECTOR-ONLY SEARCH:")
    original_results = vector_search(query, 0.35)  # Original threshold
    print(f"   Found: {len(original_results)} documents")
    
    # Test hybrid approach  
    print(f"\n2?? NEW HYBRID SEARCH:")
    hybrid_results = hybrid_search(query)
    print(f"   Found: {len(hybrid_results)} documents")
    
    # Show detailed comparison
    original_files = set(r.filename for r in original_results)
    hybrid_files = set(r.filename for r in hybrid_results)
    
    only_in_original = original_files - hybrid_files
    only_in_hybrid = hybrid_files - original_files
    in_both = original_files & hybrid_files
    
    print(f"\n?? COMPARISON SUMMARY:")
    print(f"   In both methods: {len(in_both)} files")
    print(f"   Only in original: {len(only_in_original)} files")
    print(f"   Only in hybrid: {len(only_in_hybrid)} files")
    print(f"   Improvement: +{len(only_in_hybrid)} files found")
    
    if only_in_hybrid:
        print(f"\n?? NEW FILES FOUND BY HYBRID:")
        for filename in only_in_hybrid:
            # Find the result
            result = next(r for r in hybrid_results if r.filename == filename)
            found_by = result.metadata.get("found_by", "unknown")
            print(f"   ?? {filename}")
            print(f"      Score: {result.similarity_score:.4f} | Method: {result.source_method} | Found by: {found_by}")
    
    if only_in_original:
        print(f"\n? FILES LOST IN HYBRID:")
        for filename in only_in_original:
            print(f"   ?? {filename}")
    
    # Show all results with details
    print(f"\n?? ALL HYBRID RESULTS:")
    print("-" * 80)
    for i, result in enumerate(hybrid_results, 1):
        found_by = result.metadata.get("found_by", "unknown")
        found_by_both = result.metadata.get("found_by_both", False)
        both_indicator = " ??" if found_by_both else ""
        
        print(f"{i:2d}. ?? {result.filename}")
        print(f"    ?? Score: {result.similarity_score:.4f} | Method: {result.source_method} | Found by: {found_by}{both_indicator}")
        if result.metadata.get("query_occurrences"):
            print(f"    ?? Query occurrences: {result.metadata['query_occurrences']}")
    
    return len(hybrid_results)

def test_theory():
    """Main test function"""
    print("?? HYBRID SEARCH THEORY TEST")
    print("="*50)
    
    if not CONFIG["connection_string"]:
        print("? SUPABASE_CONNECTION_STRING not found!")
        return
    
    print(f"? Environment OK (model: {CONFIG['embed_model']})")
    
    # Test with Breeda Daly
    entity = "Breeda Daly"
    total_found = compare_searches(entity)
    
    # Get expected count from database
    try:
        conn = psycopg2.connect(CONFIG["connection_string"])
        cur = conn.cursor()
        cur.execute("""
        SELECT COUNT(DISTINCT metadata->>'file_name') 
        FROM vecs.documents 
        WHERE LOWER(metadata->>'text') LIKE '%breeda daly%'
        AND metadata->>'file_name' IS NOT NULL
        """)
        expected_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        print(f"\n?? THEORY TEST RESULTS:")
        print(f"   Expected (database): {expected_count} files")
        print(f"   Found (hybrid): {total_found} files")
        
        if total_found >= expected_count:
            print(f"   ? SUCCESS: Found all or more files!")
            print(f"   ?? Theory confirmed - hybrid search works!")
        else:
            missing = expected_count - total_found
            print(f"   ?? PARTIAL: Still missing {missing} files")
            print(f"   ?? May need additional search strategies")
            
    except Exception as e:
        print(f"? Error getting expected count: {e}")

if __name__ == "__main__":
    try:
        test_theory()
    except KeyboardInterrupt:
        print("\n?? Interrupted by user")
    except Exception as e:
        print(f"? Error: {e}")