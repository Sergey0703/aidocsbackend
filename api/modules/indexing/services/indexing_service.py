#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/services/indexing_service.py
# Final version with document_registry integration

import asyncio
import logging
import time
import uuid
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..models.schemas import (
    IndexingMode,
    IndexingStatus,
    IndexingProgress,
    IndexingHistoryItem,
    ProcessingStage,
)
from .document_service import get_document_service

logger = logging.getLogger(__name__)


class IndexingTaskState:
    """State management for indexing task"""
    
    def __init__(self, task_id: str, mode: IndexingMode):
        self.task_id = task_id
        self.mode = mode
        self.status = IndexingStatus.IDLE
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        self.total_files = 0
        self.processed_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.total_chunks = 0
        self.processed_chunks = 0
        self.current_file: Optional[str] = None
        
        self.current_stage: Optional[ProcessingStage] = None
        self.current_stage_name: Optional[str] = None
        
        self.registry_entries_created = 0  # 🆕 Track registry operations
        
        self.statistics: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.cancelled = False
    
    def get_progress(self) -> IndexingProgress:
        """Get current progress"""
        elapsed_time = 0.0
        estimated_remaining = None
        progress_percentage = 0.0
        
        if self.start_time:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            
            total_items = self.total_chunks
            processed_items = self.processed_chunks
            
            if self.current_stage in [ProcessingStage.LOADING] or self.current_stage_name == "Checking for updates":
                total_items = self.total_files
                processed_items = self.processed_files

            if total_items > 0:
                progress_percentage = (processed_items / total_items) * 100 if total_items > 0 else 0
                
                if processed_items > 5 and elapsed_time > 1:
                    rate = processed_items / elapsed_time
                    remaining_items = total_items - processed_items
                    if rate > 0:
                        estimated_remaining = remaining_items / rate
        
        return IndexingProgress(
            status=self.status,
            stage=self.current_stage,
            current_stage_name=self.current_stage_name or "",
            progress_percentage=progress_percentage,
            total_files=self.total_files,
            processed_files=self.processed_files,
            failed_files=self.failed_files,
            skipped_files=self.skipped_files,
            registry_entries_created=self.registry_entries_created,  # 🆕
            total_chunks=self.total_chunks,
            processed_chunks=self.processed_chunks,
            start_time=self.start_time,
            elapsed_time=elapsed_time,
            estimated_remaining=estimated_remaining,
            current_file=self.current_file,
        )


class IndexingService:
    """Service for managing document indexing operations with real backend integration"""
    
    def __init__(self):
        self._tasks: Dict[str, IndexingTaskState] = {}
        self._history: List[IndexingHistoryItem] = []
        self._lock = asyncio.Lock()
        logger.info("✅ IndexingService initialized with backend integration")
    
    def _setup_backend_path(self):
        """Add rag_indexer to Python path"""
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent
            backend_path = project_root / "rag_indexer"
            if backend_path.exists() and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
                logger.debug(f"Added backend path: {backend_path}")
        except Exception as e:
            logger.error(f"Failed to setup backend path: {e}")
    
    async def create_task(self, mode: IndexingMode) -> str:
        async with self._lock:
            task_id = str(uuid.uuid4())
            task_state = IndexingTaskState(task_id, mode)
            self._tasks[task_id] = task_state
            logger.info(f"📝 Created indexing task: {task_id} (mode: {mode.value})")
            return task_id
    
    async def get_task(self, task_id: str) -> Optional[IndexingTaskState]:
        return self._tasks.get(task_id)
    
    async def start_indexing(
        self,
        task_id: str,
        documents_dir: Optional[str] = None,
        skip_conversion: bool = False,
        skip_indexing: bool = False,
        batch_size: Optional[int] = None,
        force_reindex: bool = False,
        delete_existing: bool = False,
    ) -> bool:
        task = await self.get_task(task_id)
        if not task:
            logger.error(f"❌ Task not found: {task_id}")
            return False
        
        task.status = IndexingStatus.RUNNING
        task.start_time = datetime.now()
        
        asyncio.create_task(
            self._run_real_indexing(
                task=task,
                documents_dir=documents_dir,
                skip_conversion=skip_conversion,
                skip_indexing=skip_indexing,
                batch_size=batch_size,
                force_reindex=force_reindex,
                delete_existing=delete_existing,
            )
        )
        logger.info(f"🚀 Started indexing task: {task_id}")
        return True

    async def _prepare_documents_for_indexing(self, documents: List[Any], task: IndexingTaskState) -> Tuple[List[Any], int]:
        """
        Filters documents, removes outdated versions from the DB, and returns a list for indexing.
        Also returns the count of skipped files.
        """
        doc_service = get_document_service()
        files_to_index = []
        files_to_skip = 0
        files_to_update = 0

        total_docs = len(documents)
        logger.info(f"🔍 Checking {total_docs} files against database for changes...")
        task.total_files = total_docs

        for i, doc in enumerate(documents):
            if task.cancelled: raise asyncio.CancelledError
            task.current_file = doc.metadata.get('file_name', 'Unknown')
            task.processed_files = i + 1

            metadata = doc.metadata
            # 🆕 FIXED: Use registry_id as unique identifier instead of original_path
            registry_id = metadata.get('registry_id')
            document_id = metadata.get('original_path')
            current_hash = metadata.get('original_file_hash')

            # If no registry_id, fall back to original_path (backward compatibility)
            unique_id = registry_id if registry_id else document_id

            if not unique_id:
                logger.warning(f"File {metadata.get('file_name')} is missing both 'registry_id' and 'original_path'. Treating as new.")
                files_to_index.append(doc)
                continue

            if not current_hash:
                logger.warning(f"File {metadata.get('file_name')} is missing 'original_file_hash'. Re-indexing for safety.")
                await doc_service.delete_records_by_document_id(unique_id)
                files_to_index.append(doc)
                files_to_update += 1
                continue

            # 🆕 FIXED: Query by registry_id if available, otherwise by document_id
            existing_records_meta = await doc_service.find_records_by_document_id(unique_id)

            if not existing_records_meta:
                # No existing records found - this is a new document
                files_to_index.append(doc)
                logger.debug(f"   ➕ New document: {metadata.get('file_name')} (registry_id: {registry_id or 'N/A'})")
            else:
                # Found existing records - check if hash changed
                stored_hash = existing_records_meta[0].get('original_file_hash')
                if stored_hash == current_hash:
                    # Same hash - skip indexing
                    files_to_skip += 1
                    logger.debug(f"   ⏩ Skipped (unchanged): {metadata.get('file_name')}")
                else:
                    # Hash changed - update
                    logger.info(f"🔄 Found updated file, removing old version: {metadata.get('file_name')}")
                    await doc_service.delete_records_by_document_id(unique_id)
                    files_to_index.append(doc)
                    files_to_update += 1
        
        logger.info(f"📊 Indexing Plan: New={len(files_to_index) - files_to_update}, Update={files_to_update}, Skip={files_to_skip}")
        return files_to_index, files_to_skip

    async def _run_real_indexing(
        self,
        task: IndexingTaskState,
        documents_dir: Optional[str],
        skip_conversion: bool,
        skip_indexing: bool,
        batch_size: Optional[int],
        force_reindex: bool,
        delete_existing: bool,
    ):
        """Run REAL document indexing using backend modules WITH REGISTRY INTEGRATION"""
        try:
            logger.info(f"🔄 Starting REAL indexing pipeline for task: {task.task_id}")
            self._setup_backend_path()
            
            from chunking_vectors.config import get_config
            from chunking_vectors.batch_processor import create_batch_processor
            from chunking_vectors.embedding_processor import create_embedding_processor
            from chunking_vectors.markdown_loader import create_markdown_loader
            from chunking_vectors.registry_manager import create_registry_manager
            from storage.storage_manager import SupabaseStorageManager  # 🆕 Added for Storage mode
            from llama_index.core.node_parser import SentenceSplitter
            from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
            from llama_index.vector_stores.supabase import SupabaseVectorStore
            
            if skip_indexing:
                logger.info("⏩ Skipping entire indexing pipeline (skip_indexing=True)")
                task.status = IndexingStatus.COMPLETED
                task.end_time = datetime.now()
                self._add_to_history(task)
                return

            config = get_config()
            if not documents_dir:
                current_file = Path(__file__)
                project_root = current_file.parent.parent.parent.parent.parent
                default_md_dir = project_root / "rag_indexer" / "data" / "markdown"
                config.DOCUMENTS_DIR = str(default_md_dir)
            else:
                config.DOCUMENTS_DIR = documents_dir
                
            logger.info(f"📁 Documents directory: {config.DOCUMENTS_DIR}")

            task.current_stage = ProcessingStage.LOADING
            task.current_stage_name = "Loading Documents"

            # 🚀 OPTIMIZATION: Use markdown_loader with Storage mode
            # It now queries for status='pending_indexing' internally, so only pending docs are loaded
            logger.info("📂 Loading pending documents from Storage using markdown_loader...")

            from chunking_vectors.markdown_loader import create_markdown_loader
            from storage.storage_manager import SupabaseStorageManager
            from chunking_vectors.registry_manager import create_registry_manager
            import tempfile

            # Initialize managers
            storage_manager = SupabaseStorageManager()
            registry_manager = create_registry_manager(config.CONNECTION_STRING)

            # Create markdown loader with Storage mode
            # Note: documents_dir is required for initialization but not used in Storage mode
            temp_dir = tempfile.gettempdir()
            loader = create_markdown_loader(
                documents_dir=temp_dir,  # Required for initialization, not used in Storage mode
                recursive=True,
                config=config,
                storage_manager=storage_manager
            )

            # Load documents - this will query for pending_indexing status automatically
            documents, loading_stats = loader.load_data(registry_manager=registry_manager)

            if not documents:
                logger.info("✅ No pending documents to index. All up to date!")
                task.status = IndexingStatus.COMPLETED
                task.end_time = datetime.now()
                self._add_to_history(task)
                return

            logger.info(f"📊 Loaded {len(documents)} pending documents from Storage")
            logger.info(f"   ✓ Registry enrichments: {loading_stats.get('registry_enrichments', 0)}")
            logger.info(f"   ✓ Total characters: {loading_stats.get('total_characters', 0):,}")
            task.total_files = len(documents)
            task.registry_entries_created = loading_stats.get('registry_enrichments', 0)

            # 🚀 OPTIMIZATION: Skip incremental checking - markdown_loader already filtered by status!
            # All loaded documents are guaranteed to be pending_indexing, so process them all

            doc_service = get_document_service()
            documents_to_process = []

            if task.mode == IndexingMode.FULL or force_reindex or delete_existing:
                # Full re-index: delete existing records first
                logger.warning(f"Full re-index for {len(documents)} docs requested. Deleting existing records...")
                task.total_files = len(documents)
                for i, doc in enumerate(documents):
                    if task.cancelled: raise asyncio.CancelledError
                    task.processed_files = i + 1
                    registry_id = doc.metadata.get('registry_id')
                    if registry_id:
                        await doc_service.delete_records_by_document_id(registry_id)
                documents_to_process = documents
            else:
                # Incremental mode: process all pending docs (already filtered by database query)
                logger.info(f"📊 Incremental mode: processing {len(documents)} pending documents")
                documents_to_process = documents
                task.skipped_files = 0  # No skips - all docs are pending

            if not documents_to_process:
                logger.info("✅ All documents are up-to-date. Nothing to index.")
                task.status = IndexingStatus.COMPLETED
                task.end_time = datetime.now()
                self._add_to_history(task)
                return

            task.current_stage = ProcessingStage.CHUNKING
            task.current_stage_name = "Chunking Documents"
            logger.info(f"✂️ Chunking {len(documents_to_process)} documents...")

            # 🆕 Set current_file to first document being processed
            if documents_to_process:
                first_file = documents_to_process[0].metadata.get('file_name', 'unknown')
                task.current_file = first_file
                logger.debug(f"   📄 Processing: {first_file}")

            # 🔄 USE UNIFIED CHUNKING from rag_indexer (supports Hybrid + SentenceSplitter)
            from chunking_vectors.chunk_helpers import create_and_filter_chunks_enhanced
            from chunking_vectors.batch_processor import create_progress_tracker

            # Create dummy node_parser for fallback (if hybrid chunking fails)
            node_parser = SentenceSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)

            # Create progress tracker
            progress_tracker = create_progress_tracker()

            # Use unified chunking (will use HybridChunker if enabled, else SentenceSplitter)
            all_nodes, invalid_nodes, chunk_stats = create_and_filter_chunks_enhanced(
                documents_to_process,
                config,
                node_parser,
                progress_tracker
            )

            task.total_chunks = len(all_nodes)
            
            if not all_nodes:
                logger.warning("⚠️ No chunks created from documents.")
                task.status = IndexingStatus.COMPLETED
                task.end_time = datetime.now()
                self._add_to_history(task)
                return
            logger.info(f"📊 Total chunks to process: {task.total_chunks}")

            # 🆕 ENSURE REGISTRY_ID IN CHUNK METADATA
            logger.info("🔗 Propagating registry_id to chunks...")
            
            chunks_with_registry = 0
            for node in all_nodes:
                if 'registry_id' not in node.metadata:
                    # Try to get from parent document
                    parent_doc = next((d for d in documents_to_process if d.id_ == node.ref_doc_id), None)
                    if parent_doc and 'registry_id' in parent_doc.metadata:
                        node.metadata['registry_id'] = parent_doc.metadata['registry_id']
                        chunks_with_registry += 1
            
            logger.info(f"   ✓ {chunks_with_registry}/{len(all_nodes)} chunks have registry_id")

            task.current_stage = ProcessingStage.EMBEDDING
            task.current_stage_name = "Generating Embeddings & Saving"
            
            vector_store = SupabaseVectorStore(postgres_connection_string=config.CONNECTION_STRING, collection_name=config.TABLE_NAME)
            embed_model = GoogleGenAIEmbedding(model_name=config.EMBED_MODEL, api_key=config.GEMINI_API_KEY)
            embedding_processor = create_embedding_processor(embed_model, vector_store, config)
            batch_processor = create_batch_processor(embedding_processor, config.PROCESSING_BATCH_SIZE, 0, config)
            
            results = batch_processor.process_all_batches(all_nodes, batch_size or config.EMBEDDING_BATCH_SIZE, config.DB_BATCH_SIZE)
            
            task.processed_chunks = results.get('total_saved', 0)
            
            # 🆕 UPDATE REGISTRY STATUS TO PROCESSED
            logger.info("✅ Updating document_registry status to 'processed'...")

            processed_registry_ids = set()
            for doc in documents_to_process:
                if 'registry_id' in doc.metadata:
                    registry_id = doc.metadata['registry_id']
                    if registry_id not in processed_registry_ids:
                        try:
                            # Use registry_manager instead of registry_service
                            registry_manager.update_registry_status(registry_id, 'processed')
                            processed_registry_ids.add(registry_id)
                        except Exception as e:
                            logger.warning(f"Failed to update registry status for {registry_id}: {e}")

            logger.info(f"   ✓ Updated {len(processed_registry_ids)} registry entries to 'processed'")
            
            task.statistics = {
                "documents_loaded": len(documents),
                "documents_processed": len(documents_to_process),
                "skipped_files": task.skipped_files,
                "chunks_created": task.total_chunks,
                "chunks_saved": task.processed_chunks,
                "success_rate": (task.processed_chunks / task.total_chunks * 100) if task.total_chunks > 0 else 100.0,
                "registry_entries_updated": len(processed_registry_ids),  # 🆕
            }

            # 🔍 DEBUG: Log statistics before adding to history
            logger.info(f"📊 Final statistics: documents_processed={task.statistics.get('documents_processed')}, "
                       f"chunks_created={task.statistics.get('chunks_created')}, "
                       f"chunks_saved={task.statistics.get('chunks_saved')}")

            # 🆕 Clear current_file when complete
            task.current_file = None
            task.processed_files = len(documents_to_process)  # Set final count

            task.status = IndexingStatus.COMPLETED
            task.current_stage = ProcessingStage.COMPLETED
            task.current_stage_name = "Completed"
            task.end_time = datetime.now()
            self._add_to_history(task)

            # Remove completed task from active tasks so status queries use history
            async with self._lock:
                if task.task_id in self._tasks:
                    del self._tasks[task.task_id]
                    logger.info(f"🗑️ Removed completed task from active tasks: {task.task_id}")

            logger.info(f"✅ REAL indexing pipeline completed for task: {task.task_id}")

        except asyncio.CancelledError:
            logger.warning(f"⚠️ Indexing task {task.task_id} was cancelled.")
            task.status = IndexingStatus.CANCELLED
            task.end_time = datetime.now()
            task.errors.append("Task was cancelled by user.")
            self._add_to_history(task)

            # Remove cancelled task from active tasks
            async with self._lock:
                if task.task_id in self._tasks:
                    del self._tasks[task.task_id]
                    logger.info(f"🗑️ Removed cancelled task from active tasks: {task.task_id}")
        except Exception as e:
            logger.error(f"❌ Indexing failed for task {task.task_id}: {e}", exc_info=True)
            task.status = IndexingStatus.FAILED
            task.end_time = datetime.now()
            task.errors.append(f"Fatal error during indexing: {str(e)}")
            self._add_to_history(task)

            # Remove failed task from active tasks
            async with self._lock:
                if task.task_id in self._tasks:
                    del self._tasks[task.task_id]
                    logger.info(f"🗑️ Removed failed task from active tasks: {task.task_id}")
    
    def _add_to_history(self, task: IndexingTaskState):
        if not task.start_time: task.start_time = datetime.now()

        files_processed_count = task.statistics.get("documents_processed", 0)
        if not isinstance(files_processed_count, int):
             files_processed_count = len(files_processed_count) if hasattr(files_processed_count, '__len__') else 0

        # 🔍 DEBUG: Log what we're storing in history
        logger.info(f"🔍 Adding to history: files_processed={files_processed_count}, "
                   f"chunks_created={task.statistics.get('chunks_created', 0)}, "
                   f"source dict: {task.statistics.get('documents_processed')}")

        history_item = IndexingHistoryItem(
            task_id=task.task_id, mode=task.mode, status=task.status,
            start_time=task.start_time, end_time=task.end_time,
            duration=(task.end_time - task.start_time).total_seconds() if task.end_time and task.start_time else 0.0,
            files_processed=files_processed_count,
            chunks_created=task.statistics.get("chunks_created", 0),
            success_rate=task.statistics.get("success_rate", 0.0),
            error_message=task.errors[0] if task.errors else None
        )
        self._history.insert(0, history_item)
        if len(self._history) > 50: self._history = self._history[:50]
        logger.info(f"📝 Added task to history: {task.task_id}")

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel running indexing task"""
        task = await self.get_task(task_id)
        if not task or task.status != IndexingStatus.RUNNING:
            logger.warning(f"Task {task_id} not found or not running, cannot cancel.")
            return False
        task.cancelled = True
        logger.info(f"⚠️ Cancelling indexing task: {task_id}")
        return True

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status"""
        task = await self.get_task(task_id)
        if not task:
            for item in self._history:
                if item.task_id == task_id:
                    # 🆕 FIXED: Return full statistics from history item
                    stats = {
                        "documents_processed": item.files_processed,
                        "chunks_created": item.chunks_created,
                        "chunks_saved": item.chunks_created,  # Assume all created chunks were saved
                        "success_rate": item.success_rate,
                    }
                    # 🔍 DEBUG: Log what we're returning from history
                    logger.info(f"🔍 Returning from history: documents_processed={stats['documents_processed']}, "
                               f"chunks_created={stats['chunks_created']}, "
                               f"history item files_processed={item.files_processed}")
                    return {
                        "task_id": item.task_id,
                        "progress": IndexingProgress(status=item.status, progress_percentage=100),
                        "statistics": stats,
                        "errors": [item.error_message] if item.error_message else [],
                        "warnings": [],
                        "timestamp": item.end_time or datetime.now()
                    }
            return None

        return {
            "task_id": task_id,
            "progress": task.get_progress(),
            "statistics": task.statistics,
            "errors": task.errors,
            "warnings": task.warnings,
            "timestamp": datetime.now()
        }

    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all active and recent tasks"""
        return [
            {
                "task_id": task_id,
                "status": task.status.value,
                "mode": task.mode.value,
                "progress_percentage": task.get_progress().progress_percentage,
                "start_time": task.start_time,
            }
            for task_id, task in self._tasks.items()
        ]

    async def clear_completed_tasks(self):
        """Clear completed, failed, or cancelled tasks from memory"""
        async with self._lock:
            self._tasks = {
                tid: t for tid, t in self._tasks.items()
                if t.status not in [IndexingStatus.COMPLETED, IndexingStatus.FAILED, IndexingStatus.CANCELLED]
            }
        logger.info("🧹 Cleared completed tasks from memory.")

    def get_active_tasks_count(self) -> int:
        """Get number of active (running) indexing tasks"""
        return sum(1 for task in self._tasks.values() if task.status == IndexingStatus.RUNNING)

    async def get_history(self, limit: int = 10) -> List[IndexingHistoryItem]:
        """Get indexing history, most recent first"""
        return self._history[:limit]

# Singleton instance
_indexing_service: Optional[IndexingService] = None


def get_indexing_service() -> IndexingService:
    """Get or create indexing service singleton"""
    global _indexing_service
    
    if _indexing_service is None:
        _indexing_service = IndexingService()
    
    return _indexing_service