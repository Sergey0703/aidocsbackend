#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified RAG Document Indexer - Main Entry Point
Part 2: Chunking & Vectors Only
Loads markdown files from Docling (Part 1) → chunks → embeddings → vector storage
UPDATED: Now integrated with document_registry for database schema compliance
"""

import logging
import sys
import os
import time
from datetime import datetime

# --- LLAMA INDEX IMPORTS ---
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.supabase import SupabaseVectorStore
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter

# --- PART 2 MODULE IMPORTS ---
from chunking_vectors.config import get_config, print_feature_status
from chunking_vectors.database_manager import create_database_manager
from chunking_vectors.registry_manager import create_registry_manager
from chunking_vectors.embedding_processor import create_embedding_processor
from chunking_vectors.batch_processor import create_batch_processor, create_progress_tracker
from chunking_vectors.utils import (
    InterruptHandler, PerformanceMonitor, StatusReporter,
    validate_python_version, print_system_info, create_run_summary,
    setup_logging_directory, safe_file_write, save_failed_files_details
)
from chunking_vectors.loading_helpers import (
    load_markdown_documents, 
    print_loading_summary,
    validate_documents_for_processing,
    print_document_validation_summary,
    check_processing_requirements,
    get_loading_recommendations,
    print_loading_recommendations
)
from chunking_vectors.analysis_helpers import (
    analyze_final_results_enhanced,
    create_enhanced_run_summary,
    create_enhanced_status_report
)
from chunking_vectors.chunk_helpers import (
    create_and_filter_chunks_enhanced,
    create_chunk_processing_report,
    save_chunk_processing_report
)


def print_simplified_info():
    """Print information about simplified system"""
    print("\n🔧 Simplified RAG System - Part 2: Chunking & Vectors")
    print("  📄 Input: Markdown files from Docling (Part 1)")
    print("  🧩 Processing: Chunking with SentenceSplitter")
    print("  🚀 Embeddings: Google Gemini API")
    print("  💾 Storage: Supabase vector database")
    print("  🔗 Registry: Document tracking enabled")
    print("  ✅ No document conversion needed")
    print("=" * 50)


def initialize_components(config):
    """
    Initialize LlamaIndex components for chunking and embeddings
    
    Args:
        config: Configuration object
    
    Returns:
        dict: Initialized components
    """
    print("🔧 Initializing LlamaIndex components...")
    
    # Vector store
    vector_store = SupabaseVectorStore(
        postgres_connection_string=config.CONNECTION_STRING,
        collection_name=config.TABLE_NAME,
        dimension=config.EMBED_DIM,
    )
    
    # Storage context
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Gemini embedding model
    embed_settings = config.get_embedding_settings()
    embed_model = GoogleGenAIEmbedding(
        model_name=embed_settings['model'],
        api_key=embed_settings['api_key'],
    )
    
    # Node parser for chunking
    chunk_settings = config.get_chunk_settings()
    node_parser = SentenceSplitter(
        chunk_size=chunk_settings['chunk_size'], 
        chunk_overlap=chunk_settings['chunk_overlap'],
        paragraph_separator="\n\n",
        secondary_chunking_regex="[.!?]\\s+",
        include_metadata=True,
        include_prev_next_rel=True
    )
    
    print("✅ Components initialized successfully")
    return {
        'vector_store': vector_store,
        'storage_context': storage_context,
        'embed_model': embed_model,
        'node_parser': node_parser
    }


def main():
    """Simplified main function - markdown → chunks → embeddings → vectors"""
    
    # Setup
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    
    # Validate environment
    if not validate_python_version():
        sys.exit(1)
    
    # Get incremental mode setting early
    incremental_mode = os.getenv("INCREMENTAL_MODE", "false").lower() == "true"
    
    # Initialize tracking
    progress_tracker = create_progress_tracker()
    performance_monitor = PerformanceMonitor()
    status_reporter = StatusReporter("Simplified RAG Indexing (Part 2: Chunking & Vectors)")
    
    # Setup logging
    log_dir = setup_logging_directory()
    
    start_time = time.time()
    progress_tracker.start()
    performance_monitor.start()
    
    # Simplified statistics tracking
    stats = {
        'start_time': start_time,
        'documents_loaded': 0,
        'chunks_created': 0,
        'valid_chunks': 0,
        'embeddings_generated': 0,
        'records_saved': 0,
        'processing_stages': []
    }
    
    # Final analysis results
    final_analysis = None
    
    # Incremental indexer (will be initialized if needed)
    incremental_indexer = None
    
    try:
        with InterruptHandler() as interrupt_handler:
            
            # ===============================================================
            # 1. CONFIGURATION LOADING
            # ===============================================================
            
            print("🔧 Loading configuration...")
            config = get_config()
            config.print_config()
            
            # Print feature status
            print_feature_status()
            
            # Print simplified system info
            print_simplified_info()
            
            progress_tracker.add_checkpoint("Configuration loaded")
            
            # Print system information
            print_system_info()
            
            # Validate Gemini API configuration
            print("🚀 Validating Gemini API configuration...")
            from chunking_vectors.config import validate_gemini_environment
            
            gemini_validation = validate_gemini_environment()
            if not gemini_validation['ready']:
                print("❌ Gemini API configuration issues detected:")
                for issue in gemini_validation['configuration_issues']:
                    print(f"   - {issue}")
                print("\nPlease fix configuration issues before proceeding.")
                sys.exit(1)
            else:
                print("✅ Gemini API configuration validated")
                print(f"   Model: {config.EMBED_MODEL}")
                print(f"   Dimension: {config.EMBED_DIM}")
                print(f"   Rate limit: {config.GEMINI_REQUEST_RATE_LIMIT} requests/sec")
            
            # Check processing requirements
            requirements_met, missing = check_processing_requirements(config)
            if not requirements_met:
                print("\n❌ Cannot proceed - missing requirements")
                sys.exit(1)
            
            # ===============================================================
            # 2. COMPONENT INITIALIZATION
            # ===============================================================
            
            components = initialize_components(config)
            progress_tracker.add_checkpoint("Components initialized")
            
            # Create processors
            db_manager = create_database_manager(config.CONNECTION_STRING, config.TABLE_NAME)
            
            # ===============================================================
            # 2.1 REGISTRY MANAGER INITIALIZATION (NEW!)
            # ===============================================================
            
            print("\n🔗 Initializing registry manager...")
            registry_manager = create_registry_manager(config.CONNECTION_STRING)
            progress_tracker.add_checkpoint("Registry manager initialized")
            print("✅ Registry manager ready - documents will be tracked in document_registry")
            
            embedding_processor = create_embedding_processor(
                components['embed_model'], 
                components['vector_store'],
                config
            )
            
            # Create batch processor (no restart interval for Gemini)
            batch_processor = create_batch_processor(
                embedding_processor, 
                config.PROCESSING_BATCH_SIZE,
                batch_restart_interval=0,  # Not needed for Gemini API
                config=config
            )
            
            # Check for interruption
            if interrupt_handler.check_interrupted():
                print("Process interrupted during initialization")
                return
            
            # ===============================================================
            # 3. MARKDOWN DOCUMENT LOADING (WITH REGISTRY ENRICHMENT)
            # ===============================================================
            
            print("\n" + "="*70)
            print("📄 LOADING MARKDOWN DOCUMENTS WITH REGISTRY ENRICHMENT")
            print("="*70)
            
            try:
                # Create markdown loader
                from chunking_vectors.markdown_loader import create_markdown_loader
                
                loader = create_markdown_loader(
                    documents_dir=config.DOCUMENTS_DIR,
                    recursive=True,
                    config=config
                )
                
                # Load documents WITH registry enrichment
                print("🔗 Loading documents with registry_id enrichment...")
                documents, loading_stats = loader.load_data(registry_manager=registry_manager)
                
                # Create processing summary
                processing_summary = {
                    'documents_loaded': len(documents),
                    'loading_stats': loading_stats,
                    'total_documents': len(documents),
                    'blacklist_applied': loading_stats.get('directories_skipped', 0) > 0,
                    'blacklisted_directories': config.BLACKLIST_DIRECTORIES,
                    'directories_scanned': loading_stats.get('directories_scanned', 0),
                    'directories_skipped': loading_stats.get('directories_skipped', 0),
                    'registry_enrichments': loading_stats.get('registry_enrichments', 0),
                    'registry_failures': loading_stats.get('registry_failures', 0),
                    'source_system': 'docling',
                    'processing_stage': 'part_2_chunking_vectors'
                }
                
                stats['processing_stages'].append('markdown_loading')
                
            except Exception as e:
                print(f"❌ Markdown loading failed: {e}")
                raise
            
            stats['documents_loaded'] = len(documents)
            
            load_time = time.time() - start_time
            
            # Print loading summary
            print_loading_summary(documents, processing_summary, load_time)
            
            # Print registry enrichment status
            registry_enrichments = processing_summary.get('registry_enrichments', 0)
            registry_failures = processing_summary.get('registry_failures', 0)
            
            print(f"\n🔗 REGISTRY ENRICHMENT RESULTS:")
            print(f"   ✅ Successful enrichments: {registry_enrichments}")
            if registry_failures > 0:
                print(f"   ❌ Failed enrichments: {registry_failures}")
                print(f"   ⚠️  WARNING: Some documents may not have registry_id!")
            else:
                print(f"   🎉 All documents successfully enriched with registry_id")
            
            # Get and print recommendations
            recommendations = get_loading_recommendations(processing_summary, config)
            print_loading_recommendations(recommendations)
            
            if not documents:
                print("⚠️ No documents found in the markdown directory.")
                print("💡 Ensure Docling (Part 1) has processed documents to markdown format.")
                return
            
            # Verify registry_id presence
            docs_without_registry = sum(1 for doc in documents if not doc.metadata.get('registry_id'))
            if docs_without_registry > 0:
                print(f"\n⚠️  CRITICAL WARNING: {docs_without_registry} documents missing registry_id!")
                print(f"   These documents will FAIL to index due to database constraints.")
                print(f"   Check logs above for registry enrichment failures.")
                
                # Ask user if they want to continue
                response = input("\nContinue anyway? (y/N): ").strip().lower()
                if response != 'y':
                    print("Indexing aborted by user.")
                    return
            
            performance_monitor.checkpoint("Markdown documents loaded", len(documents))
            stats['processing_stages'].append('documents_loaded')
            
            # ===============================================================
            # INCREMENTAL FILTERING (if enabled)
            # ===============================================================
            
            if incremental_mode:
                print(f"\n🔄 Incremental mode enabled")
                
                # Import incremental indexer
                from chunking_vectors.incremental_indexer import create_incremental_indexer
                
                # Create incremental indexer
                incremental_indexer = create_incremental_indexer(config, db_manager)
                
                # Print current state
                incremental_indexer.print_statistics()
                
                # Remove deleted files from database
                cleanup_stats = incremental_indexer.remove_deleted_files()
                
                # Filter to only new/modified documents
                new_docs, modified_docs, unchanged_docs = incremental_indexer.filter_new_and_modified(documents)
                
                # Use only new and modified
                documents = new_docs + modified_docs
                
                if not documents:
                    print("\n✅ No new or modified files to index")
                    print("All files are up to date!")
                    return True
                
                print(f"\n📊 Processing {len(documents)} files ({len(new_docs)} new, {len(modified_docs)} modified)")
            
            # Check for interruption
            if interrupt_handler.check_interrupted():
                print("Process interrupted during document loading")
                return
            
            # ===============================================================
            # 4. DELETION DIALOG
            # ===============================================================
            
            print(f"\n{'='*70}")
            print("🗑️ SAFE DELETION CHECK")
            print(f"{'='*70}")
            
            # Get file identifiers
            files_to_process = set()
            for doc in documents:
                file_path = doc.metadata.get('file_path', '')
                file_name = doc.metadata.get('file_name', '')
                if file_path:
                    files_to_process.add(file_path)
                elif file_name:
                    files_to_process.add(file_name)
            
            # Pass incremental_mode flag to deletion dialog
            deletion_info = db_manager.safe_deletion_dialog(files_to_process, incremental_mode=incremental_mode)
            progress_tracker.add_checkpoint("Deletion dialog completed")
            stats['processing_stages'].append('deletion_dialog')
            
            # Check for interruption
            if interrupt_handler.check_interrupted():
                print("Process interrupted during deletion dialog")
                return
            
            # ===============================================================
            # 5. DOCUMENT VALIDATION
            # ===============================================================
            
            # Validate documents
            documents_with_content, documents_without_content = validate_documents_for_processing(documents, config)
            
            # Print validation summary
            print_document_validation_summary(documents_with_content, documents_without_content)
            
            if not documents_with_content:
                print("❌ No documents with sufficient content found. Exiting.")
                return
            
            # ===============================================================
            # 6. CHUNK CREATION AND FILTERING
            # ===============================================================
            
            # Create and filter chunks
            valid_nodes, invalid_nodes, enhanced_node_stats = create_and_filter_chunks_enhanced(
                documents_with_content, config, components['node_parser'], progress_tracker
            )
            
            # Verify registry_id propagation to chunks
            print(f"\n🔍 Verifying registry_id propagation to chunks...")
            chunks_with_registry = sum(1 for node in valid_nodes if node.metadata.get('registry_id'))
            chunks_without_registry = len(valid_nodes) - chunks_with_registry
            
            print(f"   ✅ Chunks with registry_id: {chunks_with_registry}/{len(valid_nodes)}")
            if chunks_without_registry > 0:
                print(f"   ❌ Chunks WITHOUT registry_id: {chunks_without_registry}")
                print(f"   ⚠️  WARNING: These chunks will FAIL to save to database!")
                
                # Ask user if they want to continue
                response = input("\nContinue anyway? (y/N): ").strip().lower()
                if response != 'y':
                    print("Indexing aborted by user.")
                    return
            
            # Create chunk processing report
            chunk_report = create_chunk_processing_report(valid_nodes, invalid_nodes, enhanced_node_stats, config)
            save_chunk_processing_report(chunk_report, log_dir)
            
            stats['chunks_created'] = enhanced_node_stats['total_nodes_created']
            stats['valid_chunks'] = enhanced_node_stats['valid_nodes']
            stats['quality_analysis_results'] = {
                'filter_success_rate': enhanced_node_stats['filter_success_rate'],
                'invalid_chunks': enhanced_node_stats['invalid_nodes'],
                'avg_content_length': enhanced_node_stats['avg_content_length']
            }
            stats['processing_stages'].append('chunk_processing')
            
            if not valid_nodes:
                print("❌ No valid chunks were generated. Exiting.")
                return
            
            performance_monitor.checkpoint("Chunks processed", len(valid_nodes))
            
            # Check for interruption
            if interrupt_handler.check_interrupted():
                print("Process interrupted during chunk creation")
                return
            
            # ===============================================================
            # 7. BATCH PROCESSING WITH GEMINI API
            # ===============================================================
            
            print(f"\n🚀 Starting batch processing with Gemini API...")
            batch_settings = config.get_batch_settings()
            
            print(f"🔧 Processing Configuration:")
            print(f"   Processing batch size: {batch_settings['processing_batch_size']}")
            print(f"   Embedding batch size: {batch_settings['embedding_batch_size']}")
            print(f"   Database batch size: {batch_settings['db_batch_size']}")
            print(f"   Embedding model: {config.EMBED_MODEL} ({config.EMBED_DIM}D)")
            print(f"   Gemini rate limit: {config.GEMINI_REQUEST_RATE_LIMIT} requests/sec")
            print(f"   Gemini retry attempts: {config.GEMINI_RETRY_ATTEMPTS}")
            print(f"   🔗 Registry tracking: ENABLED")
            
            # Process all batches
            batch_results = batch_processor.process_all_batches(
                valid_nodes,
                batch_settings['embedding_batch_size'],
                batch_settings['db_batch_size']
            )
            
            # Update statistics
            stats['records_saved'] = batch_results['total_saved']
            stats['embeddings_generated'] = batch_results['total_saved']
            stats['processing_stages'].append('batch_processing')
            
            # Add batch processing stats
            stats.update({
                'total_batches': batch_results['total_batches'],
                'failed_batches': batch_results['failed_batches'],
                'total_failed_chunks': batch_results['total_failed_chunks'],
                'total_embedding_errors': batch_results['total_embedding_errors'],
                'avg_speed': batch_results['avg_speed'],
                'total_time': batch_results['total_time']
            })
            
            performance_monitor.checkpoint("Batch processing completed", batch_results['total_saved'])
            progress_tracker.add_checkpoint("Processing completed", batch_results['total_saved'])
            
            # ===============================================================
            # 7.1 UPDATE REGISTRY STATUS (NEW!)
            # ===============================================================
            
            print(f"\n🔗 Updating document registry status...")
            try:
                # Get unique registry IDs from successfully saved chunks
                registry_ids = set()
                for node in valid_nodes:
                    reg_id = node.metadata.get('registry_id')
                    if reg_id:
                        registry_ids.add(reg_id)
                
                # Update status for all processed documents
                for registry_id in registry_ids:
                    registry_manager.update_registry_status(registry_id, 'indexed')
                
                print(f"   ✅ Updated status for {len(registry_ids)} documents in registry")
                
            except Exception as e:
                print(f"   ⚠️  Warning: Could not update registry status: {e}")
            
            # ===============================================================
            # UPDATE INCREMENTAL STATE (if enabled)
            # ===============================================================
            
            if incremental_mode and incremental_indexer and documents_with_content:
                incremental_indexer.mark_batch_as_indexed(documents_with_content)
            
            # ===============================================================
            # 8. END-TO-END ANALYSIS
            # ===============================================================
            
            # Perform comprehensive analysis
            final_analysis = analyze_final_results_enhanced(config, db_manager, log_dir, stats)
            stats['processing_stages'].append('final_analysis')
            
            # ===============================================================
            # 9. FINAL RESULTS AND REPORTING
            # ===============================================================
            
            # Print final results
            success = batch_processor.print_final_results(batch_results, deletion_info)
            
            # Write comprehensive log
            batch_processor.write_comprehensive_log(
                batch_results, 
                deletion_info, 
                encoding_issues=0,  # Not applicable for markdown
                error_log_file=f"{log_dir}/indexing_errors.log"
            )
            
            # Create and save run summary
            end_time = time.time()
            
            # Get failed files list from final analysis
            failed_files_list = final_analysis.get('missing_files_detailed', []) if final_analysis else []
            
            enhanced_summary = create_enhanced_run_summary(
                start_time, end_time, stats, final_analysis, config
            )
            
            summary_file = f"{log_dir}/run_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            if safe_file_write(summary_file, enhanced_summary):
                print(f"📊 Run summary saved to: {summary_file}")
            
            # Print performance summary
            performance_monitor.print_performance_summary()
            progress_tracker.print_progress_summary()
            
            # Final status report
            create_enhanced_status_report(
                status_reporter, stats, final_analysis, batch_results, 
                deletion_info, start_time, end_time
            )
            
            status_reporter.print_report()
            
            # Final message with registry info
            print("\n" + "="*70)
            if success:
                print("✅ SUCCESS: Simplified RAG indexing completed successfully!")
                print("📊 Workflow: Markdown → Chunks → Embeddings → Vectors ✓")
                print("🔗 Registry: All documents tracked in document_registry ✓")
            else:
                print("⚠️ WARNING: Indexing completed with some errors")
                print("📊 Check logs for details")
            print("="*70)
            
            # Print registry summary
            print(f"\n🔗 REGISTRY SUMMARY:")
            print(f"   Documents enriched: {processing_summary.get('registry_enrichments', 0)}")
            print(f"   Registry failures: {processing_summary.get('registry_failures', 0)}")
            print(f"   Chunks with registry_id: {chunks_with_registry}/{len(valid_nodes)}")
            
            return success
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️ WARNING: Indexing interrupted by user.")
        if 'stats' in locals():
            print(f"📊 Partial results: {stats.get('records_saved', 0)} chunks saved")
        print(f"✅ No data was corrupted - safe to restart.")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        print(f"🔧 Check your configuration and try again.")
        
        # Try to save error information
        if 'log_dir' in locals():
            error_info = f"Indexer fatal error at {datetime.now()}: {str(e)}\n"
            safe_file_write(f"{log_dir}/fatal_error.log", error_info)
        
        import traceback
        traceback.print_exc()
        
        sys.exit(1)


if __name__ == "__main__":
    try:
        print("🚀 Simplified RAG Document Indexer - Part 2: Chunking & Vectors")
        print("=" * 70)
        print("📄 Input: Markdown files from Docling (Part 1)")
        print("🧩 Processing: Chunking → Gemini Embeddings → Supabase Vectors")
        print("🔗 Registry: Document tracking with document_registry table")
        print("=" * 70)
        
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Indexing interrupted by user.")
        print(f"✅ Safe to restart - no data corruption.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        sys.exit(1)