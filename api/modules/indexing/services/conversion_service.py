#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/services/conversion_service.py
# Final version with all methods and fixes.

import asyncio
import logging
import time
import uuid
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..models.schemas import (
    ConversionStatus,
    ConversionProgress,
    ConversionResult,
)

logger = logging.getLogger(__name__)

FILE_CONVERSION_TIMEOUT = 300  # 5 minutes

class ConversionTaskState:
    """State management for a single conversion task."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = ConversionStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_files = 0
        self.converted_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.current_file: Optional[str] = None
        self.results: List[ConversionResult] = []
        self.errors: List[str] = []
        self.cancelled = False
    
    def get_progress(self) -> ConversionProgress:
        """Calculate and return the current progress."""
        elapsed_time = 0.0
        estimated_remaining = None
        progress_percentage = 0.0
        
        if self.start_time:
            end_time = self.end_time or datetime.now()
            elapsed_time = (end_time - self.start_time).total_seconds()
            
            if self.total_files > 0:
                # --- ИСПРАВЛЕНИЕ: Считаем прогресс только от файлов в задаче ---
                processed_in_task = self.converted_files + self.failed_files
                progress_percentage = (processed_in_task / self.total_files) * 100 if self.total_files > 0 else 0
                
                if processed_in_task > 2 and elapsed_time > 1 and self.status == ConversionStatus.CONVERTING:
                    rate = processed_in_task / elapsed_time
                    remaining_files = self.total_files - processed_in_task
                    if rate > 0:
                        estimated_remaining = remaining_files / rate
        
        return ConversionProgress(
            status=self.status,
            total_files=self.total_files,
            converted_files=self.converted_files,
            failed_files=self.failed_files,
            skipped_files=self.skipped_files,
            progress_percentage=progress_percentage,
            current_file=self.current_file,
            elapsed_time=elapsed_time,
            estimated_remaining=estimated_remaining,
        )


class ConversionService:
    """Service for managing document conversion operations."""
    
    def __init__(self):
        self._tasks: Dict[str, ConversionTaskState] = {}
        self._lock = asyncio.Lock()
        logger.info("✅ ConversionService initialized")
    
    def _setup_backend_path(self):
        """Add the 'rag_indexer' directory to the Python path for backend imports."""
        try:
            current_file = Path(__file__).resolve()
            project_root = current_file.parents[4] 
            backend_path = project_root / "rag_indexer"
            if backend_path.exists() and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
                logger.debug(f"Added backend path for imports: {backend_path}")
        except Exception as e:
            logger.error(f"Failed to setup backend path: {e}", exc_info=True)
    
    async def create_task(self) -> str:
        """Create a new conversion task and return its ID."""
        async with self._lock:
            task_id = "conv_" + str(uuid.uuid4())
            self._tasks[task_id] = ConversionTaskState(task_id)
            logger.info(f"📝 Created conversion task: {task_id}")
            return task_id
    
    async def get_task(self, task_id: str) -> Optional[ConversionTaskState]:
        """Retrieve a task by its ID."""
        return self._tasks.get(task_id)
    
    async def start_conversion(
        self,
        task_id: str,
        input_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        incremental: bool = True,
        formats: Optional[List[str]] = None,
        enable_ocr: Optional[bool] = None,
        max_file_size_mb: Optional[int] = None,
    ) -> bool:
        """Start the conversion process in a background task."""
        task = await self.get_task(task_id)
        if not task:
            logger.error(f"❌ Task not found, cannot start conversion: {task_id}")
            return False
        
        task.status = ConversionStatus.CONVERTING
        task.start_time = datetime.now()
        
        asyncio.create_task(
            self._run_real_conversion(
                task=task, input_dir=input_dir, output_dir=output_dir,
                incremental=incremental, formats=formats, enable_ocr=enable_ocr,
                max_file_size_mb=max_file_size_mb,
            )
        )
        logger.info(f"🚀 Started background conversion for task: {task_id}")
        return True

    async def _run_real_conversion(
        self,
        task: ConversionTaskState,
        input_dir: Optional[str],
        output_dir: Optional[str],
        incremental: bool,
        formats: Optional[List[str]],
        enable_ocr: Optional[bool],
        max_file_size_mb: Optional[int],
    ):
        """The core logic that runs the Docling conversion process."""
        try:
            logger.info(f"📄 Starting REAL conversion pipeline for task: {task.task_id}")
            self._setup_backend_path()
            
            from docling_processor import get_docling_config, create_document_scanner, create_document_converter

            config = get_docling_config()
            
            current_file = Path(__file__).resolve()
            project_root = current_file.parents[4]
            config.RAW_DOCUMENTS_DIR = str(input_dir or project_root / "rag_indexer" / "data" / "raw")
            config.MARKDOWN_OUTPUT_DIR = str(output_dir or project_root / "rag_indexer" / "data" / "markdown")
            config.METADATA_DIR = str(Path(config.MARKDOWN_OUTPUT_DIR) / "_metadata")
            config.FAILED_CONVERSIONS_DIR = str(project_root / "rag_indexer" / "data" / "failed")
            
            if enable_ocr is not None: config.ENABLE_OCR = enable_ocr
            if max_file_size_mb is not None: config.MAX_FILE_SIZE_MB = max_file_size_mb
            if formats: config.SUPPORTED_FORMATS = formats
            
            logger.info(f"   Input dir: {config.RAW_DOCUMENTS_DIR}")
            
            scanner = create_document_scanner(config)
            files_to_process = scanner.scan_directory()
            
            if incremental:
                initial_count = len(files_to_process)
                files_to_process = scanner.filter_already_converted(files_to_process, incremental=True)
                task.skipped_files = initial_count - len(files_to_process)
            
            if not files_to_process:
                logger.info("✅ No new/modified files to convert.")
                task.status = ConversionStatus.COMPLETED
                return

            task.total_files = len(files_to_process)
            logger.info(f"   Found {task.total_files} files to convert.")

            converter = create_document_converter(config)
            
            for file_path in files_to_process:
                if task.cancelled:
                    raise asyncio.CancelledError("Task was cancelled by user.")
                
                task.current_file = file_path.name
                
                success, output_path, error = False, None, None
                start_time = time.time()

                try:
                    logger.info(f"Processing {file_path.name} in a separate thread with a {FILE_CONVERSION_TIMEOUT}s timeout...")
                    success, output_path, error = await asyncio.wait_for(
                        asyncio.to_thread(converter.convert_file, file_path),
                        timeout=FILE_CONVERSION_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    error = f"Conversion timed out after {FILE_CONVERSION_TIMEOUT} seconds."
                    logger.error(f"❌ {error} for file {file_path.name}")
                    success = False
                except Exception as e:
                    error = f"An unexpected error occurred during conversion: {e}"
                    logger.error(f"❌ {error}", exc_info=True)
                    success = False
                
                conversion_time = time.time() - start_time
                
                # 🆕 CREATE OR UPDATE REGISTRY AFTER SUCCESSFUL CONVERSION
                if success and output_path:
                    try:
                        from api.modules.vehicles.services.document_registry_service import get_document_registry_service
                        registry_service = get_document_registry_service()
                        
                        # Check if registry entry exists for this raw file
                        existing_entry = await registry_service.find_by_raw_path(str(file_path))
                        
                        if existing_entry:
                            # Update existing entry
                            await registry_service.update_registry_by_raw_path(
                                raw_file_path=str(file_path),
                                markdown_file_path=str(output_path),
                                status='pending_indexing'
                            )
                            logger.info(f"✅ Updated registry: {file_path.name} → pending_indexing")
                        else:
                            # Create new entry
                            await registry_service.create_registry_entry(
                                raw_file_path=str(file_path),
                                markdown_file_path=str(output_path),
                                status='pending_indexing'
                            )
                            logger.info(f"✅ Created registry entry: {file_path.name} → pending_indexing")
                        
                    except Exception as e:
                        logger.warning(f"Failed to update/create registry for {file_path.name}: {e}")
                        # Don't fail conversion if registry update fails
                
                result = ConversionResult(
                    filename=file_path.name,
                    status=ConversionStatus.COMPLETED if success else ConversionStatus.FAILED,
                    input_path=str(file_path),
                    output_path=str(output_path) if output_path else None,
                    file_size=file_path.stat().st_size,
                    conversion_time=conversion_time,
                    error_message=error,
                )
                task.results.append(result)
                
                if success:
                    task.converted_files += 1
                else:
                    task.failed_files += 1
                    task.errors.append(f"{file_path.name}: {error}")

            task.status = ConversionStatus.COMPLETED
            logger.info(f"✅ Conversion task {task.task_id} completed successfully.")

        except asyncio.CancelledError as e:
            logger.warning(f"⚠️ Conversion task {task.task_id} was cancelled.")
            task.status = ConversionStatus.CANCELLED
            task.errors.append(str(e))
        except Exception as e:
            logger.error(f"❌ Unhandled error in conversion task {task.task_id}: {e}", exc_info=True)
            task.status = ConversionStatus.FAILED
            task.errors.append(f"Fatal conversion error: {str(e)}")
        finally:
            task.end_time = datetime.now()
            task.current_file = None 
          
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = await self.get_task(task_id)
        if not task:
            return None
        
        return {
            "task_id": task_id,
            "progress": task.get_progress(),
            "results": task.results,
            "errors": task.errors,
            "timestamp": datetime.now()
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        task = await self.get_task(task_id)
        if task and task.status == ConversionStatus.CONVERTING:
            task.cancelled = True
            logger.info(f"Sent cancellation request to task: {task_id}")
            return True
        logger.warning(f"Cannot cancel task {task_id}: not found or not in 'converting' state.")
        return False

    async def delete_task(self, task_id: str) -> bool:
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.info(f"🗑️ Deleted conversion task from memory: {task_id}")
                return True
            return False

    def get_active_tasks_count(self) -> int:
        return sum(1 for task in self._tasks.values() if task.status == ConversionStatus.CONVERTING)

    async def get_supported_formats(self) -> Dict[str, Any]:
        try:
            self._setup_backend_path()
            from docling_processor import get_docling_config
            config = get_docling_config()
            return {
                "formats": config.SUPPORTED_FORMATS,
                "ocr_enabled": config.ENABLE_OCR,
                "max_file_size_mb": config.MAX_FILE_SIZE_MB,
            }
        except Exception as e:
            logger.error(f"Failed to get supported formats from config: {e}")
            return {
                "formats": ["pdf", "docx", "pptx", "html", "txt", "png", "jpg"],
                "ocr_enabled": True, "max_file_size_mb": 100,
            }

    async def validate_documents(
        self,
        input_dir: Optional[str] = None,
        check_formats: bool = True,
        check_size: bool = True,
        max_size_mb: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            self._setup_backend_path()
            from docling_processor import get_docling_config, create_document_scanner
            
            config = get_docling_config()
            if input_dir: config.RAW_DOCUMENTS_DIR = input_dir
            if max_size_mb: config.MAX_FILE_SIZE_MB = max_size_mb
            
            scanner = create_document_scanner(config)
            scanner.scan_directory()
            scan_stats = scanner.get_scan_stats()
            
            result = {
                "valid": scan_stats.get('supported_files', 0) > 0,
                "total_files": scan_stats.get('total_files', 0),
                "supported_files": scan_stats.get('supported_files', 0),
                "unsupported_files": scan_stats.get('unsupported_files', 0),
                "oversized_files": scan_stats.get('oversized_files', 0),
                "warnings": [], "errors": []
            }

            if result['unsupported_files'] > 0:
                result['warnings'].append(f"{result['unsupported_files']} files have unsupported formats.")
            if result['oversized_files'] > 0:
                result['warnings'].append(f"{result['oversized_files']} files exceed size limit.")
            if not result['valid']:
                result['errors'].append("No supported and valid files found for conversion.")
            
            return result
        except Exception as e:
            logger.error(f"Document validation failed: {e}", exc_info=True)
            return {"valid": False, "errors": [str(e)]}
            
    async def get_conversion_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        history = []
        sorted_tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.start_time or datetime.min,
            reverse=True
        )

        for task in sorted_tasks:
            if task.status in [ConversionStatus.COMPLETED, ConversionStatus.FAILED, ConversionStatus.CANCELLED]:
                if len(history) < limit:
                    history.append({
                        "task_id": task.task_id, "status": task.status.value,
                        "total_files": task.total_files, "converted_files": task.converted_files,
                        "failed_files": task.failed_files, "start_time": task.start_time,
                        "end_time": task.end_time,
                        "duration": (task.end_time - task.start_time).total_seconds() if task.end_time and task.start_time else None,
                    })
        return history
    
    async def retry_failed_conversions(self, original_task_id: str) -> Optional[str]:
        original_task = await self.get_task(original_task_id)
        if not original_task:
            logger.error(f"Original task for retry not found: {original_task_id}")
            return None
        
        failed_paths = [res.input_path for res in original_task.results if res.status == ConversionStatus.FAILED]
        if not failed_paths:
            logger.info(f"No failed files to retry in task {original_task_id}")
            return None
        
        logger.info(f"Creating a new task to retry {len(failed_paths)} failed files.")
        new_task_id = await self.create_task()
        # A full implementation would pass the list of failed_paths to start_conversion
        return new_task_id

# Singleton instance
_conversion_service: Optional[ConversionService] = None

def get_conversion_service() -> ConversionService:
    """Factory function to get the singleton instance of the ConversionService."""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = ConversionService()
    return _conversion_service