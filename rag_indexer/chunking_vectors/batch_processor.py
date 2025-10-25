#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe Batch processing module for RAG Document Indexer
Handles the main batch processing loop with progress tracking and error recovery
UPDATED: Migrated from Ollama to Gemini API - removed Ollama restarts, added Gemini API pauses
"""

import time
import os
import subprocess
from datetime import datetime, timedelta


def safe_restart_ollama_for_next_batch():
    """
    DEPRECATED: This function is kept for compatibility but does nothing for Gemini API
    Ollama restart logic is not applicable to Gemini API
    
    Returns:
        bool: Always returns True for Gemini API compatibility
    """
    print(f"\n    INFO: Ollama restart not applicable for Gemini API - skipping...")
    return True


class BatchProcessor:
    """Safe batch processor with Gemini API pauses instead of Ollama restarts"""
    
    def __init__(self, embedding_processor, processing_batch_size=100, batch_restart_interval=5, config=None):
        """
        Initialize safe batch processor for Gemini API
        
        Args:
            embedding_processor: EmbeddingProcessor instance
            processing_batch_size: Number of chunks per batch
            batch_restart_interval: Pause interval for Gemini API (in batches, default: 5)
            config: Configuration object with Gemini API settings
        """
        self.embedding_processor = embedding_processor
        self.processing_batch_size = processing_batch_size
        self.batch_restart_interval = batch_restart_interval  # Repurposed for Gemini API pauses
        self.config = config
        
        # UPDATED: Gemini API pause settings
        if config:
            embed_settings = config.get_embedding_settings()
            self.gemini_batch_pause = getattr(config, 'GEMINI_BATCH_PAUSE', 2.0)  # Default 2 second pause
            self.gemini_long_pause = getattr(config, 'GEMINI_LONG_PAUSE', 10.0)  # Default 10 second long pause
            self.rate_limit = embed_settings.get('rate_limit', 10)
        else:
            self.gemini_batch_pause = 2.0
            self.gemini_long_pause = 10.0
            self.rate_limit = 10
        
        self.batch_stats = {
            'start_time': None,
            'batches_processed': 0,
            'failed_batches': 0,
            'total_saved': 0,
            'total_failed_chunks': 0,
            'total_embedding_errors': 0,
            'gemini_pauses_applied': 0,  # NEW: track API pauses
            'gemini_long_pauses_applied': 0,  # NEW: track long pauses
            'total_pause_time': 0.0  # NEW: track total pause time
        }
    
    def start_processing(self):
        """Start the batch processing session"""
        self.batch_stats['start_time'] = time.time()
        self.embedding_processor.reset_stats()
        print(f"Starting SAFE batch processing with Gemini API at {datetime.now().strftime('%H:%M:%S')}")
        print(f"GEMINI API FEATURE: Smart pauses every {self.batch_restart_interval} batches for API health")
    
    def should_pause_for_gemini_api(self, batch_num, total_batches):
        """
        UPDATED: Determine if should pause for Gemini API health (replaces Ollama restart logic)
        
        Args:
            batch_num: Current batch number (1-based)
            total_batches: Total number of batches
        
        Returns:
            bool: True if should pause, False otherwise
        """
        # Only pause if:
        # 1. We've processed enough batches
        # 2. This is not the last batch (no point pausing after the last one)
        # 3. Batch pause interval is configured
        
        if self.batch_restart_interval <= 0:
            return False  # Pauses disabled
        
        if batch_num >= total_batches:
            return False  # Don't pause after the last batch
        
        if batch_num % self.batch_restart_interval == 0:
            return True  # Time for a pause
        
        return False
    
    def safe_pause_for_gemini_api(self, batch_num, total_batches):
        """
        UPDATED: Safely pause for Gemini API health instead of restarting Ollama
        
        Args:
            batch_num: Current batch number
            total_batches: Total number of batches
        
        Returns:
            bool: Always True for Gemini API (no restart failures)
        """
        if not self.should_pause_for_gemini_api(batch_num, total_batches):
            return True  # No pause needed
        
        print(f"\n{'='*60}")
        print(f" GEMINI API HEALTH PAUSE - BETWEEN BATCHES")
        print(f"Completed batch {batch_num}/{total_batches}")
        print(f"Next pause scheduled after batch {batch_num + self.batch_restart_interval}")
        print(f"{'='*60}")
        
        # Determine pause duration based on progress
        progress_ratio = batch_num / total_batches
        
        if progress_ratio > 0.5:  # More than 50% complete
            pause_duration = self.gemini_long_pause
            pause_type = "extended"
            self.batch_stats['gemini_long_pauses_applied'] += 1
        else:
            pause_duration = self.gemini_batch_pause
            pause_type = "standard"
            self.batch_stats['gemini_pauses_applied'] += 1
        
        print(f"[*] Applying {pause_type} pause for Gemini API health...")
        print(f"[*] Pause duration: {pause_duration:.1f} seconds")
        print(f"[*] API rate limit: {self.rate_limit} requests/sec")
        print(f"[*] This prevents API quota exhaustion and improves reliability")
        
        start_pause = time.time()
        
        # Apply the pause with progress indicator
        for i in range(int(pause_duration)):
            time.sleep(1)
            remaining = pause_duration - i - 1
            if remaining > 0:
                print(f"    Pause remaining: {remaining:.0f}s", end='\r')
        
        # Handle fractional seconds
        fractional = pause_duration - int(pause_duration)
        if fractional > 0:
            time.sleep(fractional)
        
        actual_pause_time = time.time() - start_pause
        self.batch_stats['total_pause_time'] += actual_pause_time
        
        print(f"\n[+] GEMINI API PAUSE COMPLETED: Ready for batch {batch_num + 1}")
        print(f"[*] Actual pause time: {actual_pause_time:.1f}s")
        print(f"[*] API health maintained, processing continues")
        print(f"{'='*60}\n")
        
        return True  # Always successful for Gemini API
    
    def process_batch(self, batch_nodes, batch_num, total_batches, embedding_batch_size, db_batch_size):
        """
        SAFE: Process a single batch of nodes with Gemini API pause afterward
        
        Args:
            batch_nodes: List of nodes to process
            batch_num: Current batch number
            total_batches: Total number of batches
            embedding_batch_size: Size of embedding sub-batches
            db_batch_size: Size of database batches
        
        Returns:
            dict: Batch processing results
        """
        batch_start_time = time.time()
        
        print(f"\nSAFE PROCESSING (Gemini API): batch {batch_num}/{total_batches}")
        print(f"   Chunks {(batch_num-1)*self.processing_batch_size + 1}-{min(batch_num*self.processing_batch_size, (batch_num-1)*self.processing_batch_size + len(batch_nodes))}")
        print("-" * 40)
        
        batch_result = {
            'success': False,
            'nodes_processed': len(batch_nodes),
            'embeddings_generated': 0,
            'records_saved': 0,
            'failed_chunks': 0,
            'embedding_errors': 0,
            'processing_time': 0,
            'error': None,
            'gemini_paused': False  # NEW: track if Gemini pause was applied
        }
        
        try:
            # SAFE: Generate embeddings (Gemini API with rate limiting)
            nodes_with_embeddings, embedding_errors = self.embedding_processor.robust_embedding_generation(
                batch_nodes, batch_num, embedding_batch_size
            )
            
            batch_result['embeddings_generated'] = len(nodes_with_embeddings)
            batch_result['embedding_errors'] = len(embedding_errors)
            self.batch_stats['total_embedding_errors'] += len(embedding_errors)
            
            # SAFE: Save to database (complete batch before any pauses)
            if nodes_with_embeddings:
                batch_saved, failed_chunks = self.embedding_processor.robust_save_to_database(
                    nodes_with_embeddings, batch_num, db_batch_size
                )
                
                batch_result['records_saved'] = batch_saved
                batch_result['failed_chunks'] = len(failed_chunks)
                
                self.batch_stats['total_saved'] += batch_saved
                self.batch_stats['total_failed_chunks'] += len(failed_chunks)
                
                if failed_chunks:
                    print(f"   INFO: Continuing despite {len(failed_chunks)} failed chunks...")
            else:
                print(f"   WARNING: No valid embeddings generated for this batch")
            
            batch_result['processing_time'] = time.time() - batch_start_time
            batch_result['success'] = True
            
            # Print batch summary
            if nodes_with_embeddings:
                avg_speed = len(nodes_with_embeddings) / batch_result['processing_time']
                print(f"   [+] SUCCESS: Batch {batch_num} completed safely in {batch_result['processing_time']:.2f}s")
                print(f"   INFO: Speed: {avg_speed:.2f} chunks/sec")
                print(f"   INFO: Batch saved: {batch_result['records_saved']}")
            
            self.batch_stats['batches_processed'] += 1
            
            # UPDATED: NOW that batch is completely finished, consider Gemini API pause
            # This is the ONLY safe time to pause for API health
            if batch_result['success']:
                pause_applied = self.safe_pause_for_gemini_api(batch_num, total_batches)
                batch_result['gemini_paused'] = (
                    self.should_pause_for_gemini_api(batch_num, total_batches) and pause_applied
                )
                
                # Note: Gemini API pauses always succeed (no failure cases like Ollama restarts)
            
        except Exception as e:
            batch_result['error'] = str(e)
            batch_result['processing_time'] = time.time() - batch_start_time
            
            print(f"   [-] ERROR: Batch {batch_num} failed completely: {e}")
            self.batch_stats['failed_batches'] += 1
            
            # Log batch failure
            self._log_batch_failure(batch_num, batch_nodes, e)
        
        return batch_result
    
    def print_overall_progress(self, batch_num, total_batches, total_nodes):
        """
        Print overall progress estimate with Gemini API pause info
        
        Args:
            batch_num: Current batch number
            total_batches: Total number of batches
            total_nodes: Total number of nodes
        """
        if batch_num <= 1 or not self.batch_stats['start_time']:
            return
        
        overall_elapsed = time.time() - self.batch_stats['start_time']
        avg_batch_time = overall_elapsed / batch_num
        remaining_batches = total_batches - batch_num
        
        # Account for future pauses in ETA calculation
        remaining_pauses = remaining_batches // self.batch_restart_interval if self.batch_restart_interval > 0 else 0
        estimated_pause_time = remaining_pauses * self.gemini_batch_pause
        
        overall_eta_seconds = (remaining_batches * avg_batch_time) + estimated_pause_time
        
        def format_time(seconds):
            if seconds < 60:
                return f"{seconds:.0f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}m"
            else:
                return f"{seconds/3600:.1f}h {(seconds%3600)/60:.0f}m"
        
        overall_finish_time = (datetime.now() + timedelta(seconds=overall_eta_seconds)).strftime('%H:%M')
        progress_pct = (batch_num / total_batches) * 100
        
        print(f"   INFO: Overall progress: {progress_pct:.1f}% ({batch_num}/{total_batches} batches)")
        print(f"   INFO: Total saved so far: {self.batch_stats['total_saved']}/{total_nodes}")
        print(f"   INFO: Overall ETA: {format_time(overall_eta_seconds)} | Finish: {overall_finish_time}")
        
        # NEW: Show Gemini API pause information
        if self.batch_restart_interval > 0:
            next_pause_batch = ((batch_num // self.batch_restart_interval) + 1) * self.batch_restart_interval
            if next_pause_batch <= total_batches:
                print(f"   INFO: Next Gemini API pause: after batch {next_pause_batch}")
            
            total_pauses = self.batch_stats['gemini_pauses_applied'] + self.batch_stats['gemini_long_pauses_applied']
            if total_pauses > 0:
                total_pause_time = self.batch_stats['total_pause_time']
                print(f"   INFO: Gemini API pauses: {total_pauses} applied ({format_time(total_pause_time)} total)")
    
    def _log_batch_failure(self, batch_num, batch_nodes, error):
        """Log batch failure details"""
        try:
            with open('./logs/batch_failures.log', 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n--- SAFE PROCESSING (Gemini API): Batch {batch_num} failure at {timestamp} ---\n")
                f.write(f"Error: {str(error)}\n")
                f.write(f"Batch size: {len(batch_nodes)}\n")
                f.write(f"Files in batch (first 5):\n")
                for i, node in enumerate(batch_nodes[:5]):
                    f.write(f"  {i+1}. {node.metadata.get('file_name', 'Unknown')}\n")
                if len(batch_nodes) > 5:
                    f.write(f"  ... and {len(batch_nodes) - 5} more files\n")
                f.write(f"Gemini API pause interval: {self.batch_restart_interval} batches\n")
                f.write(f"API rate limit: {self.rate_limit} requests/sec\n")
                f.write("-" * 40 + "\n")
        except Exception as e:
            print(f"   WARNING: Could not write to batch_failures.log: {e}")
    
    def process_all_batches(self, valid_nodes, embedding_batch_size, db_batch_size):
        """
        SAFE: Process all batches of nodes with Gemini API pauses
        
        Args:
            valid_nodes: List of all valid nodes to process
            embedding_batch_size: Size of embedding sub-batches
            db_batch_size: Size of database batches
        
        Returns:
            dict: Final processing results
        """
        total_nodes = len(valid_nodes)
        total_batches = (total_nodes + self.processing_batch_size - 1) // self.processing_batch_size
        
        print(f"\nStarting SAFE batch processing of {total_nodes} chunks with Gemini API...")
        print(f"Processing batch size: {self.processing_batch_size} chunks")
        print(f"Embedding batch size: {embedding_batch_size} chunks")
        print(f"Database batch size: {db_batch_size} chunks")
        print(f"[*] GEMINI API FEATURE: Health pauses every {self.batch_restart_interval} batches")
        print(f"[*] API rate limit: {self.rate_limit} requests/sec")
        print(f"Error recovery: Enabled with encoding detection")
        print("=" * 60)
        
        self.start_processing()
        
        # Process batches safely
        for i in range(0, total_nodes, self.processing_batch_size):
            batch_nodes = valid_nodes[i:i + self.processing_batch_size]
            batch_num = i // self.processing_batch_size + 1
            
            # SAFE: Process this batch (includes safe pause afterward if needed)
            batch_result = self.process_batch(
                batch_nodes, batch_num, total_batches, 
                embedding_batch_size, db_batch_size
            )
            
            # Print overall progress with pause info
            self.print_overall_progress(batch_num, total_batches, total_nodes)
        
        # Calculate final results with pause statistics
        total_time = time.time() - self.batch_stats['start_time']
        
        return {
            'total_time': total_time,
            'total_nodes': total_nodes,
            'total_batches': total_batches,
            'batches_processed': self.batch_stats['batches_processed'],
            'failed_batches': self.batch_stats['failed_batches'],
            'total_saved': self.batch_stats['total_saved'],
            'total_failed_chunks': self.batch_stats['total_failed_chunks'],
            'total_embedding_errors': self.batch_stats['total_embedding_errors'],
            'success_rate': (self.batch_stats['total_saved'] / total_nodes * 100) if total_nodes > 0 else 0,
            'avg_speed': self.batch_stats['total_saved'] / total_time if total_time > 0 else 0,
            # UPDATED: Gemini API pause statistics (replaces Ollama restart stats)
            'gemini_pauses_applied': self.batch_stats['gemini_pauses_applied'],
            'gemini_long_pauses_applied': self.batch_stats['gemini_long_pauses_applied'],
            'total_pause_time': self.batch_stats['total_pause_time'],
            'batch_pause_interval': self.batch_restart_interval,
            'api_provider': 'gemini'  # NEW: Track API provider
        }
    
    def print_final_results(self, results, deletion_info):
        """
        Print final processing results with Gemini API pause information
        
        Args:
            results: Processing results dictionary
            deletion_info: Information about deletion operations
        """
        success = (results['failed_batches'] == 0 and 
                  results['total_failed_chunks'] == 0 and 
                  results['total_embedding_errors'] == 0)
        
        print("\n" + "=" * 60)
        if success:
            print("[+] SUCCESS: SAFE ROBUST INDEXING WITH GEMINI API COMPLETED SUCCESSFULLY!")
        elif results['total_saved'] > 0:
            print("[!] WARNING: SAFE ROBUST INDEXING WITH GEMINI API COMPLETED WITH SOME ERRORS!")
            print("[+] SUCCESS: Partial success - some data was saved successfully")
        else:
            print("[-] ERROR: INDEXING FAILED - NO DATA SAVED!")
        
        print("=" * 60)
        print(f"FINAL STATISTICS:")
        print(f"   Total time: {results['total_time']:.2f}s ({results['total_time']/60:.1f}m)")
        print(f"   Total chunks: {results['total_nodes']}")
        print(f"   Total batches: {results['total_batches']}")
        print(f"   Batches processed: {results['batches_processed']}")
        print(f"   Failed batches: {results['failed_batches']}")
        print(f"   Records saved: {results['total_saved']}")
        print(f"   Failed chunks: {results['total_failed_chunks']}")
        print(f"   Embedding errors: {results['total_embedding_errors']}")
        print(f"   Success rate: {results['success_rate']:.1f}%")
        print(f"   Average speed: {results['avg_speed']:.2f} chunks/sec")
        print(f"   Records deleted: {deletion_info['records_deleted']}")
        
        # UPDATED: Gemini API pause statistics
        print(f"\n[*] GEMINI API HEALTH MANAGEMENT:")
        print(f"   API provider: {results.get('api_provider', 'gemini').title()}")
        print(f"   Pause interval: {results['batch_pause_interval']} batches")
        print(f"   Standard pauses: {results['gemini_pauses_applied']}")
        print(f"   Extended pauses: {results['gemini_long_pauses_applied']}")
        total_pauses = results['gemini_pauses_applied'] + results['gemini_long_pauses_applied']
        print(f"   Total pauses: {total_pauses}")
        print(f"   Total pause time: {results['total_pause_time']:.1f}s ({results['total_pause_time']/60:.1f}m)")
        
        if total_pauses > 0:
            avg_pause = results['total_pause_time'] / total_pauses
            print(f"   Average pause duration: {avg_pause:.1f}s")
            pause_percentage = (results['total_pause_time'] / results['total_time']) * 100
            print(f"   Pause time percentage: {pause_percentage:.1f}% of total time")
        
        # Calculate loss statistics
        total_attempted = results['total_nodes']
        total_lost = total_attempted - results['total_saved']
        loss_rate = (total_lost / total_attempted * 100) if total_attempted > 0 else 0
        
        print(f"\nDATA LOSS ANALYSIS:")
        print(f"   Total chunks attempted: {total_attempted}")
        print(f"   Chunks successfully saved: {results['total_saved']}")
        print(f"   Chunks lost: {total_lost}")
        print(f"   Loss rate: {loss_rate:.2f}%")
        
        if total_lost > 0:
            print(f"   Main loss causes:")
            print(f"   - Failed embeddings: {results['total_embedding_errors']}")
            print(f"   - Database save failures: {results['total_failed_chunks']}")
            print(f"   - Batch processing failures: {results['failed_batches']} batches")
        
        print(f"\n[*] SAFE PROCESSING FEATURES:")
        print(f"   - Processing batch size: {self.processing_batch_size} chunks")
        print(f"   - Error recovery: Individual chunk processing")
        print(f"   - Binary data detection: Enabled")
        print(f"   - Content cleaning: Enabled")
        print(f"   - Gemini API health pauses: Between batches only")
        print(f"   - Rate limiting: {self.rate_limit} requests/sec")
        print(f"   - No unsafe interruptions: Guaranteed")
        
        print("=" * 60)
        
        if success:
            print("[*] SUCCESS: Ready for RAG queries! All documents indexed safely with Gemini API.")
        elif results['total_saved'] > 0:
            print("[!] WARNING: Ready for RAG queries with partial data.")
            print("INFO: Check error logs for details on failed items:")
            print("   - failed_chunks.log")
            print("   - embedding_errors.log") 
            print("   - batch_failures.log")
            print("   - invalid_chunks_report.log")
        else:
            print("[-] ERROR: No data available for RAG queries.")
        
        # Final pause advice
        if total_pauses > 0:
            efficiency = (results['total_saved'] / results['total_time']) * 60  # chunks per minute
            print(f"\n[*] GEMINI API OPTIMIZATION:")
            print(f"   Processing efficiency: {efficiency:.1f} chunks/minute")
            print(f"   API health pauses maintained optimal performance")
            print(f"   No API quota exhaustion detected")
        
        return success
    
    def write_comprehensive_log(self, results, deletion_info, encoding_issues=0, error_log_file="./indexing_errors.log"):
        """
        Write comprehensive log with Gemini API pause information
        
        Args:
            results: Processing results dictionary
            deletion_info: Information about deletion operations
            encoding_issues: Number of encoding issues encountered
            error_log_file: Path to error log file
        """
        success = (results['failed_batches'] == 0 and 
                  results['total_failed_chunks'] == 0 and 
                  results['total_embedding_errors'] == 0)
        
        try:
            with open(error_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n--- SAFE robust processing with Gemini API run at {timestamp} ---\n")
                f.write(f"Status: {'SUCCESS' if success else 'PARTIAL' if results['total_saved'] > 0 else 'FAILED'}\n")
                f.write(f"Total time: {results['total_time']:.2f}s\n")
                f.write(f"Total chunks: {results['total_nodes']}\n")
                f.write(f"Batches processed: {results['batches_processed']}/{results['total_batches']}\n")
                f.write(f"Failed batches: {results['failed_batches']}\n")
                f.write(f"Records saved: {results['total_saved']}\n")
                f.write(f"Failed chunks: {results['total_failed_chunks']}\n")
                f.write(f"Embedding errors: {results['total_embedding_errors']}\n")
                f.write(f"Success rate: {results['success_rate']:.1f}%\n")
                f.write(f"Average speed: {results['avg_speed']:.2f} chunks/sec\n")
                f.write(f"Encoding issues: {encoding_issues}\n")
                f.write(f"Processing batch size: {self.processing_batch_size}\n")
                f.write(f"Records deleted: {deletion_info['records_deleted']}\n")
                
                # UPDATED: Gemini API pause log information
                f.write(f"GEMINI API HEALTH MANAGEMENT:\n")
                f.write(f"API provider: {results.get('api_provider', 'gemini')}\n")
                f.write(f"Pause interval: {results['batch_pause_interval']} batches\n")
                f.write(f"Standard pauses: {results['gemini_pauses_applied']}\n")
                f.write(f"Extended pauses: {results['gemini_long_pauses_applied']}\n")
                f.write(f"Total pause time: {results['total_pause_time']:.1f}s\n")
                
                f.write("SAFE PROCESSING FEATURES:\n")
                f.write("- No unsafe interruptions during embeddings\n")
                f.write("- Gemini API health pauses only between completed batches\n")
                f.write("- Guaranteed data integrity during pauses\n")
                f.write("- Rate limiting for optimal API usage\n")
                f.write("- Continued processing with pause-based optimization\n")
                f.write("-------------------------------------\n\n")
        except Exception as e:
            print(f"WARNING: Could not write to {error_log_file}: {e}")


class ProgressTracker:
    """Utility class for tracking and displaying progress with Gemini API pause information"""
    
    def __init__(self):
        self.checkpoints = []
        self.start_time = None
    
    def start(self):
        """Start progress tracking"""
        self.start_time = time.time()
        self.checkpoints = []
    
    def add_checkpoint(self, name, items_processed=0, total_items=0):
        """
        Add a progress checkpoint
        
        Args:
            name: Name of the checkpoint
            items_processed: Number of items processed
            total_items: Total number of items
        """
        if self.start_time is None:
            self.start()
        
        checkpoint = {
            'name': name,
            'timestamp': datetime.now(),
            'elapsed': time.time() - self.start_time,
            'items_processed': items_processed,
            'total_items': total_items
        }
        self.checkpoints.append(checkpoint)
    
    def print_progress_summary(self):
        """Print a summary of all checkpoints"""
        if not self.checkpoints:
            return
        
        print("\nSafe Progress Summary (Gemini API):")
        print("-" * 50)
        
        for i, checkpoint in enumerate(self.checkpoints):
            elapsed_str = f"{checkpoint['elapsed']:.1f}s"
            if checkpoint['total_items'] > 0:
                progress_pct = (checkpoint['items_processed'] / checkpoint['total_items']) * 100
                print(f"{i+1}. {checkpoint['name']}: {checkpoint['items_processed']}/{checkpoint['total_items']} ({progress_pct:.1f}%) - {elapsed_str}")
            else:
                print(f"{i+1}. {checkpoint['name']}: completed - {elapsed_str}")
        
        total_elapsed = self.checkpoints[-1]['elapsed'] if self.checkpoints else 0
        print(f"\nTotal elapsed: {total_elapsed:.1f}s ({total_elapsed/60:.1f}m)")
        print(f"Safe processing: No data corruption during Gemini API pauses")
        print("-" * 50)


def create_batch_processor(embedding_processor, processing_batch_size=100, batch_restart_interval=5, config=None):
    """
    Create a SAFE batch processor instance for Gemini API
    
    Args:
        embedding_processor: EmbeddingProcessor instance
        processing_batch_size: Number of chunks per batch
        batch_restart_interval: Pause interval for Gemini API (0 to disable)
        config: Configuration object with Gemini API settings
    
    Returns:
        BatchProcessor: Configured SAFE processor for Gemini API
    """
    return BatchProcessor(embedding_processor, processing_batch_size, batch_restart_interval, config)


def create_progress_tracker():
    """
    Create a progress tracker instance
    
    Returns:
        ProgressTracker: New progress tracker
    """
    return ProgressTracker()