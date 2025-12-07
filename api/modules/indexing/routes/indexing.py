#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/routes/indexing.py
# Real implementation with indexing service integration

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from ..models.schemas import (
    IndexingRequest,
    IndexingResponse,
    IndexingStatusResponse,
    IndexingHistoryResponse,
    ReindexFilesRequest,
    SuccessResponse,
    ErrorResponse,
    IndexingMode,
)
from ..services.indexing_service import get_indexing_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start", response_model=IndexingResponse, responses={500: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
async def start_indexing(
    request: IndexingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start document indexing process.
    
    Pipeline:
    - Part 1 (if not skipped): Document conversion using Docling
    - Part 2 (if not skipped): Chunking and embedding generation
    
    Modes:
    - **full**: Reindex all documents
    - **incremental**: Only new/modified documents
    
    Process runs in background. Use /status endpoint to check progress.
    
    Example:
    ```json
    {
      "mode": "incremental",
      "batch_size": 50,
      "force_reindex": false,
      "delete_existing": false
    }
    ```
    """
    try:
        service = get_indexing_service()
        
        # Check if already running
        if service.get_active_tasks_count() > 0:
            logger.warning("Indexing task already running")
            raise HTTPException(
                status_code=409,
                detail="Indexing task already running. Please wait for completion or cancel the current task."
            )
        
        # Create task
        task_id = await service.create_task(request.mode)
        
        logger.info(f"Created indexing task: {task_id} (mode: {request.mode.value})")
        
        # Start indexing in background
        background_tasks.add_task(
            service.start_indexing,
            task_id=task_id,
            documents_dir=request.documents_dir,
            skip_conversion=request.skip_conversion,
            skip_indexing=request.skip_indexing,
            batch_size=request.batch_size,
            force_reindex=request.force_reindex,
            delete_existing=request.delete_existing,
        )
        
        logger.info(f"Started indexing task in background: {task_id}")
        
        return IndexingResponse(
            success=True,
            message=f"Indexing started successfully in {request.mode.value} mode",
            task_id=task_id,
            mode=request.mode,
            files_to_process=0,  # Will be updated during processing
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start indexing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start indexing: {str(e)}"
        )


@router.post("/stop", response_model=SuccessResponse, responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
async def stop_indexing(task_id: str):
    """
    Stop running indexing task.

    - Gracefully stops current processing
    - Completes current batch before stopping
    - Returns partial results

    Args:
        task_id: ID of the task to stop
    """
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=400,
                detail="task_id is required and cannot be empty"
            )

        service = get_indexing_service()

        success = await service.cancel_task(task_id)

        if not success:
            logger.warning(f"Task not found or not running: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Task not found or not running: {task_id}"
            )

        logger.info(f"Stopped indexing task: {task_id}")

        return SuccessResponse(
            success=True,
            message=f"Indexing task {task_id} stopped successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop indexing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop indexing: {str(e)}"
        )


@router.get("/status", response_model=IndexingStatusResponse, responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
async def get_status(task_id: Optional[str] = None):
    """
    Get indexing status.
    
    - Returns current progress and statistics
    - Shows processing stage and ETA
    - Lists any errors encountered
    
    If task_id not provided, returns status of most recent task.
    
    Args:
        task_id: Optional task ID. If not provided, returns most recent task.
    """
    try:
        service = get_indexing_service()
        
        # If no task_id, try to get most recent active task
        if not task_id:
            all_tasks = await service.get_all_tasks()
            
            if not all_tasks:
                raise HTTPException(
                    status_code=404,
                    detail="No indexing tasks found. Start a new indexing task first."
                )
            
            # Get most recent task
            task_id = all_tasks[-1]['task_id']
            logger.info(f"No task_id provided, using most recent: {task_id}")
        
        status = await service.get_task_status(task_id)

        if not status:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Task not found: {task_id}"
            )

        # 🔍 DEBUG: Log progress stage
        progress = status.get('progress')
        if progress:
            stage_value = progress.stage if hasattr(progress, 'stage') else getattr(progress, 'stage', 'UNKNOWN')
            stage_name = progress.current_stage_name if hasattr(progress, 'current_stage_name') else getattr(progress, 'current_stage_name', 'UNKNOWN')
            logger.info(f"📊 Status response: stage={stage_value}, current_stage_name={stage_name}, progress_percentage={progress.progress_percentage if hasattr(progress, 'progress_percentage') else 'UNKNOWN'}")

        return IndexingStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/history", response_model=IndexingHistoryResponse)
async def get_history(limit: int = 10):
    """
    Get indexing history.
    
    Returns list of past indexing runs with:
    - Completion status
    - Processing time
    - Files processed
    - Success rate
    
    Args:
        limit: Maximum number of history items to return (default: 10)
    """
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )
        
        service = get_indexing_service()
        
        history = await service.get_history(limit=limit)
        
        # Calculate summary stats
        total_runs = len(history)
        successful_runs = [h for h in history if h.status.value == "completed"]
        failed_runs = [h for h in history if h.status.value == "failed"]
        
        last_successful = successful_runs[0].end_time if successful_runs else None
        last_failed = failed_runs[0].end_time if failed_runs else None
        
        logger.info(f"Retrieved {total_runs} history items")
        
        return IndexingHistoryResponse(
            history=history,
            total_runs=total_runs,
            last_successful_run=last_successful,
            last_failed_run=last_failed,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get history: {str(e)}"
        )


@router.delete("/clear", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}})
async def clear_index(confirm: bool = False):
    """
    Clear entire index.
    
    ⚠️ WARNING: This deletes all indexed documents!
    
    - Requires explicit confirmation
    - Cannot be undone
    - Use for testing or complete reindex
    
    Args:
        confirm: Must be true to proceed with deletion
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Set confirm=true to proceed."
        )
    
    try:
        # Import database manager
        import sys
        from pathlib import Path
        
        # Add backend path
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent
        backend_path = project_root / "rag_indexer"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        from chunking_vectors.config import get_config
        from chunking_vectors.database_manager import create_database_manager
        
        config = get_config()
        db_manager = create_database_manager(
            config.CONNECTION_STRING,
            config.TABLE_NAME
        )
        
        # Delete all records
        import psycopg2
        conn = psycopg2.connect(config.CONNECTION_STRING)
        cur = conn.cursor()
        
        cur.execute(f"SELECT COUNT(*) FROM vecs.{config.TABLE_NAME}")
        count_before = cur.fetchone()[0]
        
        cur.execute(f"DELETE FROM vecs.{config.TABLE_NAME}")
        deleted_count = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.warning(f"CLEARED INDEX: Deleted {deleted_count} records")
        
        return SuccessResponse(
            success=True,
            message=f"Index cleared successfully. Deleted {deleted_count} records."
        )
        
    except Exception as e:
        logger.error(f"Failed to clear index: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear index: {str(e)}"
        )


@router.post("/reindex", response_model=IndexingResponse, responses={500: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
async def reindex_files(
    request: ReindexFilesRequest,
    background_tasks: BackgroundTasks
):
    """
    Reindex specific files.
    
    - Deletes existing records for specified files
    - Re-processes only those files
    - Useful for fixing specific documents
    
    Example:
    ```json
    {
      "filenames": ["document1.md", "document2.md"],
      "force": true
    }
    ```
    """
    try:
        if not request.filenames or len(request.filenames) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one filename is required"
            )
        
        # Import database manager
        import sys
        from pathlib import Path
        
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent
        backend_path = project_root / "rag_indexer"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        from chunking_vectors.config import get_config
        from chunking_vectors.database_manager import create_database_manager
        
        config = get_config()
        db_manager = create_database_manager(
            config.CONNECTION_STRING,
            config.TABLE_NAME
        )
        
        # Delete existing records for these files
        deleted_count = 0
        for filename in request.filenames:
            import psycopg2
            conn = psycopg2.connect(config.CONNECTION_STRING)
            cur = conn.cursor()
            
            cur.execute(f"""
                DELETE FROM vecs.{config.TABLE_NAME}
                WHERE metadata->>'file_name' = %s
            """, (filename,))
            
            deleted_count += cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
        
        logger.info(f"Deleted {deleted_count} records for {len(request.filenames)} files")
        
        # Create indexing task
        service = get_indexing_service()
        task_id = await service.create_task(IndexingMode.INCREMENTAL)
        
        # Start indexing in background
        # Note: This will index ALL files, but since we deleted only specific ones,
        # only those will be re-indexed in incremental mode
        background_tasks.add_task(
            service.start_indexing,
            task_id=task_id,
            skip_conversion=True,  # Skip conversion, work with existing markdown
            force_reindex=request.force,
        )
        
        logger.info(f"Started reindex task: {task_id} for {len(request.filenames)} files")
        
        return IndexingResponse(
            success=True,
            message=f"Reindexing started for {len(request.filenames)} files. Deleted {deleted_count} existing records.",
            task_id=task_id,
            mode=IndexingMode.INCREMENTAL,
            files_to_process=len(request.filenames),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start reindex: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start reindex: {str(e)}"
        )


@router.get("/tasks", response_model=dict)
async def get_all_tasks():
    """
    Get all active and recent tasks.
    
    Returns list of all tasks with their current status.
    Useful for monitoring multiple concurrent operations.
    """
    try:
        service = get_indexing_service()
        tasks = await service.get_all_tasks()
        
        return {
            "success": True,
            "tasks": tasks,
            "total": len(tasks),
            "active": sum(1 for t in tasks if t['status'] == 'running')
        }
        
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tasks: {str(e)}"
        )


@router.delete("/tasks/cleanup", response_model=SuccessResponse)
async def cleanup_completed_tasks():
    """
    Clean up completed tasks from memory.
    
    Removes tasks with status: completed, failed, or cancelled.
    Keeps only active (running/idle) tasks.
    """
    try:
        service = get_indexing_service()
        
        await service.clear_completed_tasks()
        
        logger.info("Cleaned up completed tasks")
        
        return SuccessResponse(
            success=True,
            message="Completed tasks cleaned up successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup tasks: {str(e)}"
        )