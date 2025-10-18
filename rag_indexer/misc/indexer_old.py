#!/usr/bin/env python3
"""
Production RAG Document Indexer
Indexes documents from ./data folder into Supabase vector store
Supports PDF, DOCX, TXT files with error handling and logging
"""

import os
import logging
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# --- IMPORTS ---
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.node_parser import SentenceSplitter

def main():
    """Main function to run the document indexing process."""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    load_dotenv()
    
    # --- CONFIGURATION ---
    DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "./data")
    ERROR_LOG_FILE = "./indexing_errors.log"
    TABLE_NAME = os.getenv("TABLE_NAME", "documents")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "mxbai-embed-large")
    EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "256"))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", "10"))
    
    # --- CONNECTION ---
    connection_string = os.getenv("SUPABASE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("SUPABASE_CONNECTION_STRING not found in .env file!")
    
    print(f"=== RAG Document Indexer ===")
    print(f"Documents directory: {DOCUMENTS_DIR}")
    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Chunk size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    print(f"Vector dimension: {EMBED_DIM}")
    print("=" * 50)
    
    print("Initializing LlamaIndex components...")
    vector_store = SupabaseVectorStore(
        postgres_connection_string=connection_string,
        collection_name=TABLE_NAME,
        dimension=EMBED_DIM,
    )
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    
    node_parser = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    
    # --- INDEXING PROCESS ---
    print(f"Loading documents from folder: {DOCUMENTS_DIR}")
    start_time = time.time()
    
    try:
        reader = SimpleDirectoryReader(DOCUMENTS_DIR, recursive=True)
        documents = reader.load_data(num_workers=4)
    except Exception as e:
        print(f"ERROR: Failed to load documents: {e}")
        return
    
    load_time = time.time() - start_time
    print(f"Successfully loaded {len(documents)} document objects in {load_time:.2f} seconds.")
    
    if not documents:
        print("ERROR: No documents found in the specified directory.")
        return
    
    # --- DELETE EXISTING RECORDS FOR THESE FILES ---
    print("Checking for existing records to update...")
    files_to_process = set()
    
    for doc in documents:
        file_path = doc.metadata.get('file_path', '')
        file_name = doc.metadata.get('file_name', '')
        if file_path:
            files_to_process.add(file_path)
        elif file_name:
            files_to_process.add(file_name)
    
    deletion_info = {'files_processed': 0, 'records_deleted': 0}
    
    if files_to_process:
        print(f"Removing existing records for {len(files_to_process)} files...")
        
        try:
            # Connect directly to database to delete existing records
            conn = psycopg2.connect(connection_string)
            cur = conn.cursor()
            
            deleted_count = 0
            for file_identifier in files_to_process:
                # Delete by file_path or file_name in metadata
                cur.execute("""
                    DELETE FROM vecs.documents 
                    WHERE metadata->>'file_path' = %s 
                       OR metadata->>'file_name' = %s
                """, (file_identifier, file_identifier))
                deleted_count += cur.rowcount
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"Successfully removed {deleted_count} existing records.")
            deletion_info = {
                'files_processed': len(files_to_process),
                'records_deleted': deleted_count
            }
            
        except Exception as e:
            print(f"Warning: Could not remove existing records: {e}")
            print("Continuing with indexing (may create duplicates)...")
            deletion_info = {
                'files_processed': len(files_to_process),
                'records_deleted': f'Error: {str(e)}'
            }
    
    # --- DOCUMENT FILTERING AND VALIDATION ---
    documents_with_content = []
    failed_documents = []
    stats = {
        'total_loaded': len(documents),
        'empty_docs': 0,
        'short_docs': 0,
        'successful_docs': 0
    }

    for doc in documents:
        file_name = doc.metadata.get('file_name', 'Unknown File')
        file_path = doc.metadata.get('file_path', file_name)
        text_content = doc.text.strip()
        
        if not text_content:
            # Completely empty document
            failed_documents.append(f"{file_path} - EMPTY (no text extracted)")
            stats['empty_docs'] += 1
        elif len(text_content) < MIN_CHUNK_LENGTH:
            # Too short document
            failed_documents.append(f"{file_path} - TOO SHORT ({len(text_content)} chars)")
            stats['short_docs'] += 1
        else:
            documents_with_content.append(doc)
            stats['successful_docs'] += 1

    # Write detailed statistics to log
    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"--- Indexing run at {timestamp} ---\n")
        f.write(f"Total documents loaded: {stats['total_loaded']}\n")
        f.write(f"Files processed for deletion: {deletion_info['files_processed']}\n")
        f.write(f"Records deleted from database: {deletion_info['records_deleted']}\n")
        f.write(f"Empty documents: {stats['empty_docs']}\n")
        f.write(f"Too short documents (< {MIN_CHUNK_LENGTH} chars): {stats['short_docs']}\n")
        f.write(f"Successfully processed: {stats['successful_docs']}\n")
        if failed_documents:
            f.write("Problematic files (full paths):\n")
            for issue in failed_documents:
                f.write(f"  - {issue}\n")
        f.write("-------------------------------------\n\n")

    if failed_documents:
        print(f"Found {len(failed_documents)} problematic documents. Details logged to {ERROR_LOG_FILE}")

    if not documents_with_content:
        print("ERROR: No documents with sufficient text content found. Exiting.")
        return

    print(f"Processing {len(documents_with_content)} documents with valid content.")

    # --- MANUAL PROCESSING AND SAVING ---
    print("Manually processing and adding nodes to vector store...")
    chunk_start_time = time.time()
    
    try:
        nodes = node_parser.get_nodes_from_documents(documents_with_content, show_progress=True)
    except Exception as e:
        print(f"ERROR: Failed to parse documents into chunks: {e}")
        return
    
    chunk_time = time.time() - chunk_start_time
    print(f"Document chunking completed in {chunk_time:.2f} seconds")
    
    # Final validation of chunks
    original_node_count = len(nodes)
    valid_nodes = []
    
    for node in nodes:
        content = node.get_content().strip()
        if content and len(content) >= MIN_CHUNK_LENGTH:
            valid_nodes.append(node)
    
    filtered_count = original_node_count - len(valid_nodes)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} empty/short text chunks during processing.")

    if not valid_nodes:
        print("ERROR: No valid text chunks were generated. Exiting.")
        return

    # Process metadata for each chunk
    for node in valid_nodes:
        if 'file_name' not in node.metadata:
             node.metadata['file_name'] = node.get_metadata_str()
        node.metadata['text'] = node.get_content()
        # Add indexing timestamp
        node.metadata['indexed_at'] = datetime.now().isoformat()
    
    print(f"Generating embeddings for {len(valid_nodes)} valid chunks...")
    embedding_start_time = time.time()
    embedding_errors = 0
    
    for i, node in enumerate(valid_nodes):
        try:
            node.embedding = embed_model.get_text_embedding(node.get_content())
            
            # Show progress every 25 chunks
            if (i + 1) % 25 == 0:
                elapsed = time.time() - embedding_start_time
                avg_time = elapsed / (i + 1)
                remaining = (len(valid_nodes) - i - 1) * avg_time
                print(f"   Progress: {i+1}/{len(valid_nodes)} chunks | "
                      f"Avg: {avg_time:.2f}s/chunk | "
                      f"ETA: {remaining/60:.1f} min")
                
        except Exception as e:
            print(f"Error generating embedding for chunk {i+1}: {e}")
            embedding_errors += 1
            node.embedding = None
    
    embedding_time = time.time() - embedding_start_time
    print(f"Embedding generation completed in {embedding_time:.2f} seconds")
    
    if embedding_errors > 0:
        print(f"WARNING: {embedding_errors} chunks had embedding errors")
    
    # Filter nodes with successfully created embeddings
    nodes_with_embeddings = [node for node in valid_nodes if node.embedding is not None]
    
    if not nodes_with_embeddings:
        print("ERROR: No chunks with valid embeddings. Exiting.")
        return
    
    print(f"Adding {len(nodes_with_embeddings)} chunks to vector store...")
    db_start_time = time.time()
    
    try:
        vector_store.add(nodes_with_embeddings, batch_size=20)
        db_time = time.time() - db_start_time
        print(f"Database insertion completed in {db_time:.2f} seconds")
    except Exception as e:
        print(f"ERROR adding to vector store: {e}")
        return
    
    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print("?? INDEXING COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print(f"??  TOTAL PROCESSING TIME: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
    print(f"?? FINAL STATISTICS:")
    print(f"   ?? Total documents loaded: {stats['total_loaded']} ({load_time:.2f}s)")
    print(f"   ? Documents processed: {stats['successful_docs']}")
    print(f"   ???  Records deleted: {deletion_info['records_deleted']}")
    print(f"   ?? Chunks created: {len(nodes_with_embeddings)} ({chunk_time:.2f}s)")
    print(f"   ?? Embeddings generated: {len(nodes_with_embeddings)} ({embedding_time:.2f}s)")
    print(f"   ?? Database insertion: {db_time:.2f}s")
    print(f"   ?? Model: {EMBED_MODEL} (dim: {EMBED_DIM})")
    print(f"   ??  Settings: chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}, min_length={MIN_CHUNK_LENGTH}")
    
    if failed_documents:
        print(f"   ??  Problematic files: {len(failed_documents)} (see {ERROR_LOG_FILE})")
    
    print("=" * 50)
    print("Ready for RAG queries! Start the Streamlit app to test.")

# --- Entry point ---
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nIndexing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        sys.exit(1)