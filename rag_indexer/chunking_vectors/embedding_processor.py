#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe Embedding processing module for RAG Document Indexer
Handles embedding generation, node cleaning, and database saving
UPDATED: Migrated from Ollama to Gemini API - removed unsafe Ollama restarts, added Gemini API rate limiting
"""

import time
import os
from datetime import datetime, timedelta


def clean_json_recursive(obj):
    """Recursively clean null bytes from all strings in JSON-like structure"""
    if isinstance(obj, dict):
        return {k: clean_json_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_recursive(v) for v in obj]
    elif isinstance(obj, str):
        # Remove null bytes and limit string length
        cleaned = obj.replace('\u0000', '').replace('\x00', '')
        return cleaned[:1000]  # Limit metadata string length
    else:
        return obj


def clean_problematic_node(node):
    """
    Clean problematic metadata and content from a node -  !
    
    Args:
        node: Node object to clean
    
    Returns:
        Node: Cleaned node object
    """
    try:
        # Create a copy of the node
        cleaned_node = type(node)(
            text=node.text,
            metadata=node.metadata.copy(),
            embedding=node.embedding
        )
        
        # Clean problematic characters from content
        content = cleaned_node.get_content()
        
        # Remove null bytes (\u0000) and other problematic characters -  !
        content = content.replace('\u0000', '').replace('\x00', '').replace('\x01', '').replace('\x02', '')
        
        # Remove control characters (except newlines and tabs)
        cleaned_content = ''.join(char for char in content 
                                if ord(char) >= 32 or char in '\n\t\r')
        
        # Limit content length to prevent oversized chunks
        if len(cleaned_content) > 50000:  # 50KB limit
            cleaned_content = cleaned_content[:50000] + "... [TRUNCATED]"
        
        # Update the node's text
        cleaned_node.text = cleaned_content
        cleaned_node.metadata['text'] = cleaned_content
        
        # Clean metadata values recursively ( !)
        cleaned_node.metadata = clean_json_recursive(cleaned_node.metadata)
        
        # :    LlamaIndex  null bytes
        if hasattr(cleaned_node, 'id_') and cleaned_node.id_:
            cleaned_node.id_ = str(cleaned_node.id_).replace('\u0000', '').replace('\x00', '')
        
        if hasattr(cleaned_node, 'doc_id') and cleaned_node.doc_id:
            cleaned_node.doc_id = str(cleaned_node.doc_id).replace('\u0000', '').replace('\x00', '')
        
        #  ref_doc_id  
        if hasattr(cleaned_node, 'ref_doc_id') and cleaned_node.ref_doc_id:
            cleaned_node.ref_doc_id = str(cleaned_node.ref_doc_id).replace('\u0000', '').replace('\x00', '')
        
        #  source_node  
        if hasattr(cleaned_node, 'source_node') and cleaned_node.source_node:
            if hasattr(cleaned_node.source_node, 'node_id'):
                cleaned_node.source_node.node_id = str(cleaned_node.source_node.node_id).replace('\u0000', '').replace('\x00', '')
        
        # Add warning flag
        cleaned_node.metadata['cleaned'] = True
        cleaned_node.metadata['original_length'] = len(content)
        
        return cleaned_node
        
    except Exception as e:
        print(f"   WARNING: Error cleaning node: {e}")
        # Return original node if cleaning fails
        return node


def aggressive_clean_all_nodes(nodes):
    """
       nodes  null bytes    
    
    Args:
        nodes: List of nodes to clean
    
    Returns:
        List of cleaned nodes
    """
    cleaned_nodes = []
    
    for node in nodes:
        try:
            #    
            cleaned_node = clean_problematic_node(node)
            
            #   -    
            for attr_name in dir(cleaned_node):
                if not attr_name.startswith('_'):  # Skip private attributes
                    try:
                        attr_value = getattr(cleaned_node, attr_name)
                        if isinstance(attr_value, str):
                            cleaned_value = attr_value.replace('\u0000', '').replace('\x00', '')
                            setattr(cleaned_node, attr_name, cleaned_value)
                    except:
                        pass  # Skip if can't access or modify
            
            cleaned_nodes.append(cleaned_node)
            
        except Exception as e:
            print(f"   WARNING: Failed to clean node completely: {e}")
            # Fallback - try basic cleaning
            try:
                basic_cleaned = clean_problematic_node(node)
                cleaned_nodes.append(basic_cleaned)
            except:
                print(f"   ERROR: Node completely corrupted, skipping...")
                continue
    
    return cleaned_nodes


class EmbeddingProcessor:
    """Safe processor for generating embeddings and handling database operations with Gemini API rate limiting"""
    
    def __init__(self, embed_model, vector_store, config=None):
        """
        Initialize safe embedding processor with Gemini API support
        
        Args:
            embed_model: Embedding model instance (Gemini)
            vector_store: Vector store instance for database operations
            config: Configuration object with Gemini API settings
        """
        self.embed_model = embed_model
        self.vector_store = vector_store
        self.config = config
        
        # UPDATED: Gemini API rate limiting settings
        if config:
            embed_settings = config.get_embedding_settings()
            self.rate_limit = embed_settings.get('rate_limit', 10)  # requests per second
            self.retry_attempts = embed_settings.get('retry_attempts', 3)
            self.retry_delay = embed_settings.get('retry_delay', 1.0)
            self.timeout = embed_settings.get('timeout', 300)
        else:
            # Default Gemini API settings
            self.rate_limit = 10
            self.retry_attempts = 3
            self.retry_delay = 1.0
            self.timeout = 300
        
        # Rate limiting state
        self.last_request_time = 0
        self.request_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 0
        
        self.stats = {
            'total_processed': 0,
            'successful_embeddings': 0,
            'failed_embeddings': 0,
            'successful_saves': 0,
            'failed_saves': 0,
            'gemini_api_calls': 0,  # NEW: Track Gemini API calls
            'rate_limit_delays': 0,  # NEW: Track rate limit delays
            'retry_attempts_used': 0  # NEW: Track retry attempts
        }
    
    def _apply_rate_limit(self):
        """
        Apply rate limiting for Gemini API calls
        """
        if self.request_interval <= 0:
            return
        
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_interval:
            sleep_time = self.request_interval - time_since_last_request
            time.sleep(sleep_time)
            self.stats['rate_limit_delays'] += 1
        
        self.last_request_time = time.time()
    
    def validate_content_for_embedding(self, content):
        """
        Validate content before embedding generation -  
        
        Args:
            content: Text content to validate
        
        Returns:
            tuple: (is_valid, reason)
        """
        # Check minimum length
        if len(content.strip()) < 10:
            return False, f"too_short ({len(content)} chars)"
        
        #   :       
        #           
        sample = content[:1000]  #    1000 
        
        #      ""
        allowed_special = set('\n\t\r\f\v\x0b\x0c')
        
        #  ""  ()
        truly_binary = 0
        for c in sample:
            if ord(c) < 32:  #  
                if c not in '\n\t\r':  #  
                    truly_binary += 1
            elif ord(c) > 127:  #  UTF-8
                if c not in allowed_special:  #   
                    # ,        
                    if not (c.isprintable() or c.isspace() or c.isalnum()):
                        truly_binary += 1
        
        binary_ratio = truly_binary / len(sample) if sample else 0
        
        #   :    90%!
        if binary_ratio > 0.9:  #     90%
            return False, f"binary_data_detected ({binary_ratio:.1%})"
        
        #     -  
        letters_digits = sum(1 for c in sample if c.isalnum())
        text_ratio = letters_digits / len(sample) if sample else 0
        
        #   : /  10%!
        if text_ratio < 0.1:  #    10%
            return False, f"low_text_quality ({text_ratio:.1%})"
        
        #  :       
        words = content.split()
        if len(words) < 3:
            return False, f"too_few_words ({len(words)} words)"
        
        return True, "valid"
    
    def generate_embedding_for_node(self, node, chunk_index=0):
        """
        SAFE: Generate embedding for a single node using Gemini API with rate limiting and retries
        
        Args:
            node: Node object to process
            chunk_index: Index of chunk for logging
        
        Returns:
            tuple: (success, error_info)
        """
        try:
            content = node.get_content()
            
            # Validate content
            is_valid, reason = self.validate_content_for_embedding(content)
            if not is_valid:
                return False, f"validation_failed: {reason}"
            
            # UPDATED: Gemini API call with rate limiting and retries
            for attempt in range(self.retry_attempts + 1):
                try:
                    # Apply rate limiting before API call
                    self._apply_rate_limit()
                    
                    # Generate embedding using Gemini API
                    embedding = self.embed_model.get_text_embedding(content)
                    node.embedding = embedding
                    
                    self.stats['successful_embeddings'] += 1
                    self.stats['gemini_api_calls'] += 1
                    
                    return True, None
                    
                except Exception as api_error:
                    self.stats['retry_attempts_used'] += 1
                    
                    if attempt < self.retry_attempts:
                        # Wait before retry with exponential backoff
                        wait_time = self.retry_delay * (2 ** attempt)
                        print(f"   WARNING: Gemini API error (attempt {attempt + 1}/{self.retry_attempts + 1}), retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries exhausted
                        error_info = {
                            'chunk_index': chunk_index,
                            'file_name': node.metadata.get('file_name', 'Unknown'),
                            'error': str(api_error),
                            'content_preview': content[:100] + "..." if len(content) > 100 else content,
                            'api_provider': 'gemini',
                            'retry_attempts_used': self.retry_attempts
                        }
                        self.stats['failed_embeddings'] += 1
                        return False, error_info
            
        except Exception as e:
            error_info = {
                'chunk_index': chunk_index,
                'file_name': node.metadata.get('file_name', 'Unknown'),
                'error': str(e),
                'content_preview': content[:100] + "..." if len(content) > 100 else content,
                'api_provider': 'gemini',
                'general_error': True
            }
            self.stats['failed_embeddings'] += 1
            return False, error_info
    
    def robust_embedding_generation(self, batch_nodes, batch_num, embedding_batch_size=5):
        """
        SAFE: Generate embeddings for a batch of nodes with robust error handling and Gemini API optimizations
        
        Args:
            batch_nodes: List of nodes to process
            batch_num: Batch number for logging
            embedding_batch_size: Size of sub-batches for processing
        
        Returns:
            tuple: (nodes_with_embeddings, embedding_errors)
        """
        print(f"Generating embeddings for {len(batch_nodes)} chunks using Gemini API...")
        embedding_start_time = time.time()
        
        nodes_with_embeddings = []
        embedding_errors = []
        
        # Process embeddings in smaller sub-batches with Gemini API rate limiting
        for j in range(0, len(batch_nodes), embedding_batch_size):
            sub_batch = batch_nodes[j:j + embedding_batch_size]
            
            for i, node in enumerate(sub_batch):
                chunk_index = j + i
                # Update total processed counter for statistics
                self.stats['total_processed'] += 1
                
                # SAFE: Generate embedding with Gemini API rate limiting
                success, error_info = self.generate_embedding_for_node(node, chunk_index)
                
                if success:
                    nodes_with_embeddings.append(node)
                else:
                    if isinstance(error_info, dict):
                        embedding_errors.append(error_info)
                        file_name = error_info.get('file_name', 'Unknown')
                        error_msg = error_info.get('error', str(error_info))
                        api_provider = error_info.get('api_provider', 'unknown')
                        print(f"   ERROR: {api_provider.title()} API error for chunk {chunk_index+1} from {file_name}: {error_msg[:50]}...")
                    else:
                        print(f"   WARNING: Skipping chunk {chunk_index+1}: {error_info}")
            
            # Safe progress update with detailed timestamps and Gemini API stats
            self._print_progress_update(j, batch_nodes, embedding_start_time, batch_num, embedding_batch_size, len(nodes_with_embeddings))
        
        # Final statistics with Gemini API metrics
        embedding_time = time.time() - embedding_start_time
        final_speed = len(nodes_with_embeddings) / embedding_time if embedding_time > 0 else 0
        
        print(f"Safe Gemini API embedding generation completed in {embedding_time:.2f} seconds")
        print(f"Average speed: {final_speed:.2f} chunks/second")
        print(f"Gemini API calls: {self.stats['gemini_api_calls']}")
        print(f"Rate limit delays: {self.stats['rate_limit_delays']}")
        if self.stats['retry_attempts_used'] > 0:
            print(f"Retry attempts used: {self.stats['retry_attempts_used']}")
        
        if embedding_errors:
            print(f"   WARNING: {len(embedding_errors)} embedding errors")
            self._log_embedding_errors(embedding_errors, batch_num)
        
        return nodes_with_embeddings, embedding_errors
    
    def _print_progress_update(self, j, batch_nodes, start_time, batch_num, embedding_batch_size, successful_count):
        """Print detailed progress update with Gemini API metrics"""
        processed_in_batch = min(j + embedding_batch_size, len(batch_nodes))
        elapsed = time.time() - start_time
        chunks_per_second = successful_count / elapsed if elapsed > 0 else 0
        remaining_chunks = len(batch_nodes) - processed_in_batch
        eta_seconds = remaining_chunks / chunks_per_second if chunks_per_second > 0 else 0
        
        # Format time function
        def format_time(seconds):
            if seconds < 60:
                return f"{seconds:.0f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h {(seconds%3600)/60:.0f}m"
        
        progress_pct = (processed_in_batch / len(batch_nodes)) * 100
        current_time = datetime.now().strftime('%H:%M:%S')
        finish_time = (datetime.now() + timedelta(seconds=eta_seconds)).strftime('%H:%M')
        
        print(f"   Gemini API progress: batch {batch_num} ({progress_pct:.1f}%) | "
              f"Processed: {processed_in_batch}/{len(batch_nodes)} chunks | "
              f"Speed: {chunks_per_second:.1f} chunks/sec | "
              f"Elapsed: {format_time(elapsed)} | "
              f"ETA: {format_time(eta_seconds)} | "
              f"Time: {current_time} | "
              f"Finish: {finish_time}")
        
        # Show checkpoint every 20 sub-batches with API stats
        if (j // embedding_batch_size + 1) % 20 == 0:
            checkpoint_time = datetime.now().strftime('%H:%M:%S')
            api_calls = self.stats['gemini_api_calls']
            rate_delays = self.stats['rate_limit_delays']
            print(f"   GEMINI API CHECKPOINT at {checkpoint_time}: {processed_in_batch}/{len(batch_nodes)} chunks complete")
            print(f"   API calls: {api_calls}, Rate delays: {rate_delays}")
    
    def _log_embedding_errors(self, embedding_errors, batch_num):
        """Log embedding errors to file with Gemini API context"""
        try:
            with open('./logs/embedding_errors.log', 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n--- Gemini API embedding errors in batch {batch_num} at {timestamp} ---\n")
                for error in embedding_errors:
                    f.write(f"File: {error.get('file_name', 'Unknown')}\n")
                    f.write(f"Chunk: {error.get('chunk_index', 'Unknown')}\n")
                    f.write(f"API Provider: {error.get('api_provider', 'unknown')}\n")
                    f.write(f"Error: {error.get('error', 'Unknown')}\n")
                    f.write(f"Preview: {error.get('content_preview', 'N/A')}\n")
                    if error.get('retry_attempts_used'):
                        f.write(f"Retry attempts: {error['retry_attempts_used']}\n")
                    f.write("-" * 40 + "\n")
        except Exception as e:
            print(f"   WARNING: Could not write to embedding_errors.log: {e}")
    
    def robust_save_to_database(self, nodes_with_embeddings, batch_num, db_batch_size=25):
        """
        SAFE: Save nodes to database with robust error handling
        UPDATED: Now properly handles registry_id column for new database schema
        
        Args:
            nodes_with_embeddings: List of nodes with embeddings
            batch_num: Batch number for logging
            db_batch_size: Size of database batches
        
        Returns:
            tuple: (total_saved, failed_chunks)
        """
        print(f"Safely saving {len(nodes_with_embeddings)} chunks to database...")
        db_start_time = time.time()
        
        total_saved = 0
        failed_chunks = []
        
        #  :    nodes  !
        print(f"   INFO: Safely cleaning all nodes from null bytes before database save...")
        cleaned_nodes = aggressive_clean_all_nodes(nodes_with_embeddings)
        print(f"   INFO: Safely cleaned {len(cleaned_nodes)} nodes (original: {len(nodes_with_embeddings)})")
        
        # CRITICAL: Use direct SQL to handle registry_id column
        import psycopg2
        import json
        from psycopg2.extras import execute_values
        
        try:
            # Get database connection
            conn = psycopg2.connect(self.config.CONNECTION_STRING)
            cur = conn.cursor()
            
            # Prepare data for batch insert
            data_to_insert = []
            nodes_without_registry = []
            
            for node in cleaned_nodes:
                registry_id = node.metadata.get('registry_id')
                
                if not registry_id:
                    # Track nodes without registry_id
                    nodes_without_registry.append(node.metadata.get('file_name', 'Unknown'))
                    continue
                
                # Prepare data tuple: (id, registry_id, vec, metadata)
                data_to_insert.append((
                    str(node.id_),
                    str(registry_id),
                    node.embedding,
                    json.dumps(node.metadata)
                ))
            
            # Warn about missing registry_ids
            if nodes_without_registry:
                print(f"   WARNING: {len(nodes_without_registry)} chunks missing registry_id, skipping...")
                for file_name in set(nodes_without_registry)[:5]:
                    print(f"      - {file_name}")
            
            if not data_to_insert:
                print(f"   ERROR: No valid chunks to save (all missing registry_id)")
                cur.close()
                conn.close()
                return 0, []
            
            # Batch insert with registry_id
            table_name = self.config.TABLE_NAME if hasattr(self.config, 'TABLE_NAME') else 'documents'
            
            execute_values(
                cur,
                f"""
                INSERT INTO vecs.{table_name} (id, registry_id, vec, metadata)
                VALUES %s
                ON CONFLICT (id) DO UPDATE 
                SET registry_id = EXCLUDED.registry_id,
                    vec = EXCLUDED.vec,
                    metadata = EXCLUDED.metadata
                """,
                data_to_insert,
                page_size=db_batch_size
            )
            
            conn.commit()
            total_saved = len(data_to_insert)
            self.stats['successful_saves'] += total_saved
            
            db_time = time.time() - db_start_time
            print(f"   SUCCESS: Safely saved {total_saved} records with registry_id in {db_time:.2f}s")
            
            cur.close()
            conn.close()
            
            return total_saved, []
            
        except Exception as e:
            print(f"   WARNING: Batch save failed: {e}")
            print(f"   INFO: Trying individual safe chunk processing...")
            
            # If batch save fails, try saving chunks individually
            try:
                conn = psycopg2.connect(self.config.CONNECTION_STRING)
                cur = conn.cursor()
                
                for i, node in enumerate(cleaned_nodes):
                    try:
                        registry_id = node.metadata.get('registry_id')
                        
                        if not registry_id:
                            file_name = node.metadata.get('file_name', 'Unknown')
                            failed_info = {
                                'chunk_index': i,
                                'file_name': file_name,
                                'file_path': node.metadata.get('file_path', 'Unknown'),
                                'error': 'Missing registry_id',
                                'content_preview': node.get_content()[:100],
                                'content_length': len(node.get_content())
                            }
                            failed_chunks.append(failed_info)
                            self.stats['failed_saves'] += 1
                            continue
                        
                        # Double-clean problematic chunks for safety
                        ultra_cleaned_node = clean_problematic_node(node)
                        
                        # Individual insert
                        table_name = self.config.TABLE_NAME if hasattr(self.config, 'TABLE_NAME') else 'documents'
                        
                        cur.execute(
                            f"""
                            INSERT INTO vecs.{table_name} (id, registry_id, vec, metadata)
                            VALUES (%s, %s, %s, %s::jsonb)
                            ON CONFLICT (id) DO UPDATE 
                            SET registry_id = EXCLUDED.registry_id,
                                vec = EXCLUDED.vec,
                                metadata = EXCLUDED.metadata
                            """,
                            (
                                str(ultra_cleaned_node.id_),
                                str(registry_id),
                                ultra_cleaned_node.embedding,
                                json.dumps(ultra_cleaned_node.metadata)
                            )
                        )
                        conn.commit()
                        
                        total_saved += 1
                        self.stats['successful_saves'] += 1
                        
                    except Exception as chunk_error:
                        # Log the problematic chunk details
                        file_name = node.metadata.get('file_name', 'Unknown')
                        file_path = node.metadata.get('file_path', 'Unknown')
                        chunk_preview = node.get_content()[:100] + "..." if len(node.get_content()) > 100 else node.get_content()
                        
                        failed_info = {
                            'chunk_index': i,
                            'file_name': file_name,
                            'file_path': file_path,
                            'error': str(chunk_error),
                            'content_preview': chunk_preview,
                            'content_length': len(node.get_content())
                        }
                        failed_chunks.append(failed_info)
                        self.stats['failed_saves'] += 1
                        
                        print(f"   ERROR: Failed to save chunk {i+1}: {file_name}")
                        print(f"      Error: {str(chunk_error)[:100]}...")
                
                cur.close()
                conn.close()
                
            except Exception as conn_error:
                print(f"   ERROR: Could not establish individual save connection: {conn_error}")
            
            db_time = time.time() - db_start_time
            
            if total_saved > 0:
                print(f"   SUCCESS: Safely saved {total_saved} records individually in {db_time:.2f}s")
            
            if failed_chunks:
                print(f"   WARNING: Failed to save {len(failed_chunks)} problematic chunks")
                self._log_failed_chunks(failed_chunks, batch_num)
            
            return total_saved, failed_chunks
    
    def _log_failed_chunks(self, failed_chunks, batch_num):
        """Log failed chunks to file"""
        try:
            with open('./logs/failed_chunks.log', 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n--- Safe processing - Failed chunks in batch {batch_num} at {timestamp} ---\n")
                for failed in failed_chunks:
                    f.write(f"File: {failed['file_name']}\n")
                    f.write(f"Path: {failed['file_path']}\n")
                    f.write(f"Error: {failed['error']}\n")
                    f.write(f"Content length: {failed['content_length']}\n")
                    f.write(f"Preview: {failed['content_preview']}\n")
                    f.write("-" * 40 + "\n")
        except Exception as e:
            print(f"   WARNING: Could not write to failed_chunks.log: {e}")
    
    def get_processing_stats(self):
        """
        Get processing statistics with Gemini API metrics
        
        Returns:
            dict: Processing statistics including Gemini API data
        """
        return {
            'total_processed': self.stats['total_processed'],
            'successful_embeddings': self.stats['successful_embeddings'],
            'failed_embeddings': self.stats['failed_embeddings'],
            'successful_saves': self.stats['successful_saves'],
            'failed_saves': self.stats['failed_saves'],
            'embedding_success_rate': (self.stats['successful_embeddings'] / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0,
            'save_success_rate': (self.stats['successful_saves'] / (self.stats['successful_saves'] + self.stats['failed_saves']) * 100) if (self.stats['successful_saves'] + self.stats['failed_saves']) > 0 else 0,
            # NEW: Gemini API specific metrics
            'gemini_api_calls': self.stats['gemini_api_calls'],
            'rate_limit_delays': self.stats['rate_limit_delays'],
            'retry_attempts_used': self.stats['retry_attempts_used'],
            'api_provider': 'gemini'
        }
    
    def print_processing_summary(self):
        """Print processing statistics summary with Gemini API metrics"""
        stats = self.get_processing_stats()
        
        print(f"\nSafe Gemini API Embedding Processing Summary:")
        print(f"  Total chunks processed: {stats['total_processed']}")
        print(f"  Successful embeddings: {stats['successful_embeddings']}")
        print(f"  Failed embeddings: {stats['failed_embeddings']}")
        print(f"  Embedding success rate: {stats['embedding_success_rate']:.1f}%")
        print(f"  Successful saves: {stats['successful_saves']}")
        print(f"  Failed saves: {stats['failed_saves']}")
        print(f"  Save success rate: {stats['save_success_rate']:.1f}%")
        print(f"  Gemini API calls: {stats['gemini_api_calls']}")
        print(f"  Rate limit delays: {stats['rate_limit_delays']}")
        print(f"  Retry attempts used: {stats['retry_attempts_used']}")
        print(f"  Safe processing: Gemini API with rate limiting and retries")
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            'total_processed': 0,
            'successful_embeddings': 0,
            'failed_embeddings': 0,
            'successful_saves': 0,
            'failed_saves': 0,
            'gemini_api_calls': 0,
            'rate_limit_delays': 0,
            'retry_attempts_used': 0
        }


class NodeProcessor:
    """Safe processor for handling node operations and validation"""
    
    def __init__(self, min_chunk_length=100):
        """
        Initialize safe node processor
        
        Args:
            min_chunk_length: Minimum length for valid chunks
        """
        self.min_chunk_length = min_chunk_length
    
    def validate_node(self, node):
        """
        Validate a node for processing
        
        Args:
            node: Node to validate
        
        Returns:
            tuple: (is_valid, reason)
        """
        content = node.get_content().strip()
        
        if not content:
            return False, "empty_content"
        
        if len(content) < self.min_chunk_length:
            return False, f"too_short ({len(content)} chars)"
        
        if len(content.split()) <= 5:
            return False, "too_few_words"
        
        if content.isdigit():
            return False, "only_digits"
        
        return True, "valid"
    
    def enhance_node_metadata(self, node, indexed_at=None):
        """
        Safely enhance node metadata with additional information
        CRITICAL: Preserve registry_id from parent document
        """
        if indexed_at is None:
            indexed_at = datetime.now().isoformat()
        
        content = node.get_content()
        
        # CRITICAL: Preserve registry_id if it exists
        registry_id = node.metadata.get('registry_id')
        
        # Add basic metadata if missing
        if 'file_name' not in node.metadata:
            node.metadata['file_name'] = node.get_metadata_str()
        
        # Add content metadata safely
        node.metadata.update({
            'text': content,
            'indexed_at': indexed_at,
            'content_length': len(content),
            'word_count': len(content.split()),
            'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
            'safe_processing_enabled': True,
            'api_provider': 'gemini'
        })
        
        # Ensure registry_id is present (CRITICAL!)
        if registry_id:
            node.metadata['registry_id'] = registry_id
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Node for {node.metadata.get('file_name')} is missing registry_id!")
        
        return node

    def filter_and_enhance_nodes(self, all_nodes, show_progress=True):
        """
        Safely filter and enhance a list of nodes
        
        Args:
            all_nodes: List of nodes to process
            show_progress: Whether to show progress updates
        
        Returns:
            tuple: (valid_nodes, invalid_nodes_info)
        """
        valid_nodes = []
        invalid_nodes = []
        
        total_nodes = len(all_nodes)
        indexed_at = datetime.now().isoformat()
        
        # Track invalid files
        invalid_files_summary = {}
        
        for i, node in enumerate(all_nodes):
            if show_progress and i % 1000 == 0:
                print(f"  Safe processing nodes: {i}/{total_nodes}")
            
            is_valid, reason = self.validate_node(node)
            
            if is_valid:
                enhanced_node = self.enhance_node_metadata(node, indexed_at)
                valid_nodes.append(enhanced_node)
            else:
                file_name = node.metadata.get('file_name', 'Unknown')
                
                invalid_info = {
                    'node_index': i,
                    'reason': reason,
                    'content_preview': node.get_content()[:100],
                    'file_name': file_name,
                    'content_length': len(node.get_content())
                }
                invalid_nodes.append(invalid_info)
                
                # Count invalid reasons per file
                if file_name not in invalid_files_summary:
                    invalid_files_summary[file_name] = {}
                if reason not in invalid_files_summary[file_name]:
                    invalid_files_summary[file_name][reason] = 0
                invalid_files_summary[file_name][reason] += 1
        
        if show_progress:
            print(f"  Safe node filtering complete: {len(valid_nodes)} valid, {len(invalid_nodes)} invalid")
            
            # Print detailed invalid files report
            if invalid_files_summary:
                print(f"\nInvalid chunks by file:")
                for file_name, reasons in invalid_files_summary.items():
                    total_invalid = sum(reasons.values())
                    reasons_str = ", ".join([f"{reason}: {count}" for reason, count in reasons.items()])
                    print(f"  {file_name}: {total_invalid} invalid chunks ({reasons_str})")
                    
                # Save detailed report to file
                self._save_invalid_chunks_report(invalid_files_summary, invalid_nodes)
        
        return valid_nodes, invalid_nodes
    
    def _save_invalid_chunks_report(self, invalid_files_summary, invalid_nodes):
        """Save detailed report of invalid chunks to file"""
        try:
            report_file = './logs/invalid_chunks_report.log'
            with open(report_file, 'w', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"Safe Processing - Invalid Chunks Report - {timestamp}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write("SUMMARY BY FILE:\n")
                f.write("-" * 30 + "\n")
                for file_name, reasons in invalid_files_summary.items():
                    total_invalid = sum(reasons.values())
                    f.write(f"\nFile: {file_name}\n")
                    f.write(f"Total invalid chunks: {total_invalid}\n")
                    for reason, count in reasons.items():
                        f.write(f"  - {reason}: {count} chunks\n")
                
                f.write(f"\n\nDETAILED INVALID CHUNKS:\n")
                f.write("-" * 30 + "\n")
                for invalid in invalid_nodes[:50]:  # First 50 examples
                    f.write(f"\nFile: {invalid['file_name']}\n")
                    f.write(f"Reason: {invalid['reason']}\n")
                    f.write(f"Content length: {invalid['content_length']}\n")
                    f.write(f"Preview: {invalid['content_preview']}\n")
                    f.write("-" * 20 + "\n")
                
                if len(invalid_nodes) > 50:
                    f.write(f"\n... and {len(invalid_nodes) - 50} more invalid chunks\n")
            
            print(f"Safe processing - detailed invalid chunks report saved to: {report_file}")
            
        except Exception as e:
            print(f"WARNING: Could not save invalid chunks report: {e}")
    
    def get_node_statistics(self, nodes):
        """
        Get statistics about a list of nodes
        
        Args:
            nodes: List of nodes to analyze
        
        Returns:
            dict: Node statistics
        """
        if not nodes:
            return {'total': 0}
        
        content_lengths = [len(node.get_content()) for node in nodes]
        word_counts = [len(node.get_content().split()) for node in nodes]
        
        # Group by file
        files = {}
        for node in nodes:
            file_name = node.metadata.get('file_name', 'Unknown')
            if file_name not in files:
                files[file_name] = 0
            files[file_name] += 1
        
        return {
            'total': len(nodes),
            'avg_content_length': sum(content_lengths) / len(content_lengths),
            'min_content_length': min(content_lengths),
            'max_content_length': max(content_lengths),
            'avg_word_count': sum(word_counts) / len(word_counts),
            'min_word_count': min(word_counts),
            'max_word_count': max(word_counts),
            'unique_files': len(files),
            'chunks_per_file': sum(files.values()) / len(files),
            'safe_processing_enabled': True,
            'api_provider': 'gemini'  # NEW: Track API provider
        }


def create_embedding_processor(embed_model, vector_store, config=None):
    """
    Create a SAFE embedding processor instance with Gemini API support
    
    Args:
        embed_model: Embedding model instance (Gemini)
        vector_store: Vector store instance
        config: Configuration object with Gemini API settings
    
    Returns:
        EmbeddingProcessor: Configured SAFE processor with Gemini API
    """
    return EmbeddingProcessor(embed_model, vector_store, config)


def create_node_processor(min_chunk_length=100):
    """
    Create a SAFE node processor instance
    
    Args:
        min_chunk_length: Minimum length for valid chunks
    
    Returns:
        NodeProcessor: Configured SAFE processor
    """
    return NodeProcessor(min_chunk_length)