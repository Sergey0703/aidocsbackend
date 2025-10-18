#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Pipeline - Complete Document Processing
Orchestrates the full pipeline: Raw Documents → Markdown → Vectors

Workflow:
    Part 1 (Docling): Raw docs → Markdown
    Part 2 (LlamaIndex): Markdown → Chunks → Embeddings → Vectors
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
import warnings

# Suppress Pydantic warning from llama-index library
# Root cause: llama_index/core/node_parser/interface.py uses deprecated 'validate_default' attribute
# This is not our code - suppressing to keep console output clean
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    module='pydantic._internal._generate_schema',
    message='.*validate_default.*'
)

# Import Part 1: Docling
from docling_processor import (
    get_docling_config,
    create_document_scanner,
    create_document_converter
)

# Import Part 2: Chunking & Vectors
from chunking_vectors.config import get_config as get_chunking_config
from indexer import main as run_indexer


class PipelineOrchestrator:
    """Orchestrator for the complete RAG pipeline"""
    
    def __init__(self, incremental=False, skip_conversion=False, skip_indexing=False):
        """
        Initialize pipeline orchestrator
        
        Args:
            incremental: Only process new/modified files
            skip_conversion: Skip Part 1 (Docling conversion)
            skip_indexing: Skip Part 2 (Vector indexing)
        """
        self.incremental = incremental
        self.skip_conversion = skip_conversion
        self.skip_indexing = skip_indexing
        
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_time': 0,
            'conversion_stats': None,
            'indexing_stats': None,
            'documents_converted': 0,
            'chunks_indexed': 0,
            'success': False
        }
    
    def print_banner(self):
        """Print pipeline banner"""
        print("\n" + "=" * 70)
        print("🚀 RAG COMPLETE PIPELINE")
        print("=" * 70)
        print("📄 Part 1: Raw Documents → Markdown (Docling)")
        print("🧩 Part 2: Markdown → Chunks → Vectors (LlamaIndex + Gemini)")
        print("=" * 70)
        
        mode = "INCREMENTAL" if self.incremental else "FULL"
        print(f"Mode: {mode}")
        
        if self.skip_conversion:
            print("⚠️  Skipping Part 1 (Conversion)")
        if self.skip_indexing:
            print("⚠️  Skipping Part 2 (Indexing)")
        
        print("=" * 70 + "\n")
    
    def run_part1_conversion(self):
        """
        Run Part 1: Document conversion
        
        Returns:
            dict: Conversion statistics
        """
        if self.skip_conversion:
            print("⏩ Skipping Part 1: Document conversion")
            return {'skipped': True}
        
        print("\n" + "=" * 70)
        print("📄 PART 1: DOCUMENT CONVERSION (Docling)")
        print("=" * 70)
        
        try:
            # Load configuration
            print("\n🔧 Loading Docling configuration...")
            config = get_docling_config()
            
            # Create scanner
            print("\n📂 Scanning for documents...")
            scanner = create_document_scanner(config)
            files_to_process = scanner.scan_directory()
            
            if not files_to_process:
                print("\n⚠️ No files found to convert")
                return {'files': 0, 'success': True, 'skipped': False}
            
            # Filter already converted (if incremental)
            if self.incremental:
                files_to_process = scanner.filter_already_converted(
                    files_to_process,
                    incremental=True
                )
                
                if not files_to_process:
                    print("\n✅ All files already converted")
                    return {'files': 0, 'success': True, 'skipped': False, 'already_converted': True}
            
            # Create converter
            print("\n🔄 Initializing converter...")
            converter = create_document_converter(config)
            
            # Convert documents
            start_time = time.time()
            results = converter.convert_batch(files_to_process)
            conversion_time = time.time() - start_time
            
            # Store stats
            self.stats['documents_converted'] = results['successful']
            
            print(f"\n✅ Part 1 completed in {conversion_time/60:.1f} minutes")
            print(f"   Converted: {results['successful']}/{results['total_files']} files")
            
            return {
                'success': results['failed'] == 0,
                'total': results['total_files'],
                'successful': results['successful'],
                'failed': results['failed'],
                'time': conversion_time,
                'skipped': False
            }
            
        except Exception as e:
            print(f"\n❌ Part 1 failed: {e}")
            return {'success': False, 'error': str(e), 'skipped': False}
    
    def run_part2_indexing(self):
        """
        Run Part 2: Vector indexing (with optional incremental mode)
        
        Returns:
            bool: Success status
        """
        if self.skip_indexing:
            print("⏩ Skipping Part 2: Vector indexing")
            return True
        
        print("\n" + "=" * 70)
        print("🧩 PART 2: VECTOR INDEXING (LlamaIndex + Gemini)")
        print("=" * 70)
        
        try:
            # Check if markdown files exist
            config = get_chunking_config()
            markdown_dir = Path(config.DOCUMENTS_DIR)
            
            if not markdown_dir.exists():
                print(f"\n❌ Markdown directory not found: {markdown_dir}")
                print("   Run Part 1 first to convert documents")
                return False
            
            # Count markdown files
            markdown_files = list(markdown_dir.glob("**/*.md"))
            # Filter out _metadata directory
            markdown_files = [f for f in markdown_files if '_metadata' not in f.parts]
            
            if not markdown_files:
                print(f"\n⚠️ No markdown files found in {markdown_dir}")
                print("   Run Part 1 first to convert documents")
                return False
            
            print(f"\n📄 Found {len(markdown_files)} markdown files")
            
            # Set incremental mode via environment variable
            if self.incremental:
                print(f"🔄 Incremental mode: ENABLED")
                import os
                os.environ['INCREMENTAL_MODE'] = 'true'
            else:
                print(f"🔄 Incremental mode: DISABLED (full reindex)")
            
            # Run indexer
            start_time = time.time()
            success = run_indexer()
            indexing_time = time.time() - start_time
            
            print(f"\n✅ Part 2 completed in {indexing_time/60:.1f} minutes")
            
            return success
            
        except Exception as e:
            print(f"\n❌ Part 2 failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_pipeline(self):
        """
        Run the complete pipeline
        
        Returns:
            bool: True if successful
        """
        self.stats['start_time'] = time.time()
        
        # Print banner
        self.print_banner()
        
        # Part 1: Document Conversion
        conversion_results = self.run_part1_conversion()
        self.stats['conversion_stats'] = conversion_results
        
        if not conversion_results.get('skipped', False) and not conversion_results.get('success', False):
            print("\n❌ Pipeline stopped: Part 1 failed")
            self.stats['success'] = False
            self._print_final_summary()
            return False
        
        # Part 2: Vector Indexing
        indexing_success = self.run_part2_indexing()
        self.stats['indexing_stats'] = {'success': indexing_success}
        
        if not indexing_success and not self.skip_indexing:
            print("\n❌ Pipeline stopped: Part 2 failed")
            self.stats['success'] = False
            self._print_final_summary()
            return False
        
        # Success!
        self.stats['end_time'] = time.time()
        self.stats['total_time'] = self.stats['end_time'] - self.stats['start_time']
        self.stats['success'] = True
        
        self._print_final_summary()
        
        return True
    
    def _print_final_summary(self):
        """Print final pipeline summary"""
        print("\n" + "=" * 70)
        print("📊 PIPELINE SUMMARY")
        print("=" * 70)
        
        if self.stats['start_time'] and self.stats['end_time']:
            total_time = self.stats['total_time']
            print(f"⏱️  Total time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
        
        # Part 1 stats
        if self.stats['conversion_stats']:
            conv = self.stats['conversion_stats']
            print(f"\n📄 Part 1 (Conversion):")
            
            if conv.get('skipped'):
                print(f"   ⏩ Skipped by user")
            elif conv.get('already_converted'):
                print(f"   ✅ All files already converted (incremental mode)")
            else:
                print(f"   Files processed: {conv.get('total', 0)}")
                print(f"   ✅ Successful: {conv.get('successful', 0)}")
                print(f"   ❌ Failed: {conv.get('failed', 0)}")
                if conv.get('time'):
                    print(f"   ⏱️  Time: {conv['time']/60:.1f} minutes")
        
        # Part 2 stats
        if self.stats['indexing_stats']:
            idx = self.stats['indexing_stats']
            print(f"\n🧩 Part 2 (Indexing):")
            
            if self.skip_indexing:
                print(f"   ⏩ Skipped by user")
            elif idx.get('success'):
                print(f"   ✅ Completed successfully")
                print(f"   Check database for indexed vectors")
            else:
                print(f"   ❌ Failed (see logs above)")
        
        # Final status
        print(f"\n" + "=" * 70)
        if self.stats['success']:
            print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
            print("🎉 Your RAG system is ready to use")
        else:
            print("❌ PIPELINE COMPLETED WITH ERRORS")
            print("⚠️  Check logs above for details")
        
        print("=" * 70 + "\n")


def main():
    """Main function"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="RAG Complete Pipeline - Document to Vectors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (convert all + index all)
  python pipeline.py
  
  # Incremental (only new/modified files)
  python pipeline.py --incremental
  
  # Only conversion
  python pipeline.py --documents-only
  
  # Only indexing
  python pipeline.py --indexing-only
  
  # Full reindex (convert all + reindex all)
  python pipeline.py --full
        """
    )
    
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Process only new/modified files'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Force full reprocessing of all files'
    )
    
    parser.add_argument(
        '--documents-only',
        action='store_true',
        help='Run only Part 1 (document conversion)'
    )
    
    parser.add_argument(
        '--indexing-only',
        action='store_true',
        help='Run only Part 2 (vector indexing)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.documents_only and args.indexing_only:
        print("❌ Error: Cannot use --documents-only and --indexing-only together")
        sys.exit(1)
    
    if args.incremental and args.full:
        print("❌ Error: Cannot use --incremental and --full together")
        sys.exit(1)
    
    # Determine mode
    incremental = args.incremental
    skip_conversion = args.indexing_only
    skip_indexing = args.documents_only
    
    # Run pipeline
    try:
        orchestrator = PipelineOrchestrator(
            incremental=incremental,
            skip_conversion=skip_conversion,
            skip_indexing=skip_indexing
        )
        
        success = orchestrator.run_pipeline()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()