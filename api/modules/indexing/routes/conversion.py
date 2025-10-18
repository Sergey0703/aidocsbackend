#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/routes/conversion.py
# Real implementation with ConversionService integration

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional

from ..models.schemas import (
    ConversionRequest,
    ConversionResponse,
    ConversionStatusResponse,
    SupportedFormatsResponse,
    ConversionResult,
    ConversionProgress,
    ConversionStatus,
    ErrorResponse,
    SuccessResponse,
)
from ..services.conversion_service import get_conversion_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/start", response_model=ConversionResponse, responses={500: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
async def start_conversion(
    request: ConversionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start document conversion process (Docling - Part 1).
    
    **Converts raw documents to markdown:**
    - PDF → Markdown
    - DOCX → Markdown
    - PPTX → Markdown
    - HTML → Markdown
    - Images → Markdown (with OCR)
    
    **Pipeline:**
    1. Scans input directory for supported formats
    2. Converts each document using Docling
    3. Saves markdown to output directory
    4. Extracts and saves metadata
    
    **Parameters:**
    - `input_dir` - Custom input directory (overrides config)
    - `output_dir` - Custom output directory (overrides config)
    - `incremental` - Skip already converted files (default: true)
    - `formats` - Specific formats to convert (e.g., ['pdf', 'docx'])
    - `enable_ocr` - Enable OCR for images (overrides config)
    - `max_file_size_mb` - Maximum file size limit (overrides config)
    
    **Example:**
    ```json
    {
      "incremental": true,
      "formats": ["pdf", "docx"],
      "enable_ocr": true,
      "max_file_size_mb": 50
    }
    ```
    
    Process runs in background. Use `/status` endpoint to check progress.
    """
    try:
        # Get conversion service
        service = get_conversion_service()
        
        # Check if conversion already running
        active_count = service.get_active_tasks_count()
        if active_count > 0:
            logger.warning("Conversion task already running")
            raise HTTPException(
                status_code=409,
                detail="Conversion task already running. Please wait for completion or cancel current task."
            )
        
        # Create conversion task
        task_id = await service.create_task()
        
        logger.info(f"Created conversion task: {task_id}")
        
        # Start conversion in background
        background_tasks.add_task(
            service.start_conversion,
            task_id=task_id,
            input_dir=request.input_dir,
            output_dir=request.output_dir,
            incremental=request.incremental,
            formats=request.formats,
            enable_ocr=request.enable_ocr,
            max_file_size_mb=request.max_file_size_mb,
        )
        
        logger.info(f"Started conversion task in background: {task_id}")
        
        # Get supported formats
        formats_info = await service.get_supported_formats()
        supported_formats = formats_info.get('formats', ["pdf", "docx", "pptx", "html", "png", "jpg"])
        
        return ConversionResponse(
            success=True,
            message="Document conversion started successfully",
            task_id=task_id,
            files_to_convert=0,  # Will be updated during scanning
            supported_formats=supported_formats,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start conversion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start conversion: {str(e)}"
        )


@router.get("/status", response_model=ConversionStatusResponse, responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
async def get_conversion_status(task_id: Optional[str] = None):
    """
    Get conversion process status.
    
    **Returns:**
    - Current progress (files converted)
    - Processing stage
    - ETA for completion
    - List of converted files
    - Any errors encountered
    
    **Parameters:**
    - `task_id` - Conversion task ID (optional, uses latest if not provided)
    
    **Progress tracking:**
    - `status` - pending, converting, completed, failed
    - `progress_percentage` - 0-100%
    - `current_file` - Currently converting file
    - `estimated_remaining` - Seconds until completion
    
    **Example response:**
    ```json
    {
      "task_id": "conv_abc123",
      "progress": {
        "status": "converting",
        "total_files": 10,
        "converted_files": 7,
        "progress_percentage": 70.0,
        "current_file": "report.pdf"
      }
    }
    ```
    """
    try:
        # Get conversion service
        service = get_conversion_service()
        
        # If no task_id provided, get most recent task
        if not task_id:
            # For now, require task_id
            # In production, implement get_latest_task()
            raise HTTPException(
                status_code=400,
                detail="task_id is required. Provide the task ID from conversion start response."
            )
        
        # Get task status
        status = await service.get_task_status(task_id)
        
        if not status:
            logger.warning(f"Conversion task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Conversion task not found: {task_id}"
            )
        
        return ConversionStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversion status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """
    Get list of supported document formats.
    
    **Returns:**
    - All supported file extensions
    - OCR capability status
    - Maximum file size limit
    - Additional conversion settings
    
    **Supported formats:**
    - **Documents:** PDF, DOCX, DOC, PPTX, PPT
    - **Text:** TXT, HTML, HTM
    - **Images:** PNG, JPG, JPEG, TIFF (with OCR)
    
    **OCR features:**
    - Text extraction from images
    - Scanned PDF support
    - Multiple language support
    - Table extraction
    
    Use this endpoint to validate file formats before upload/conversion.
    """
    try:
        # Get conversion service
        service = get_conversion_service()
        
        # Get supported formats
        formats_info = await service.get_supported_formats()
        
        return SupportedFormatsResponse(
            formats=formats_info.get('formats', []),
            ocr_enabled=formats_info.get('ocr_enabled', True),
            max_file_size_mb=formats_info.get('max_file_size_mb', 100),
        )
        
    except Exception as e:
        logger.error(f"Failed to get supported formats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get formats: {str(e)}"
        )


@router.get("/results", response_model=ConversionStatusResponse, responses={404: {"model": ErrorResponse}})
async def get_conversion_results(
    task_id: str,
    include_failed: bool = True,
    include_skipped: bool = False
):
    """
    Get detailed conversion results.
    
    **Returns for each file:**
    - Conversion status (success/failed)
    - Output markdown path
    - Conversion time
    - File size statistics
    - Error message (if failed)
    
    **Filters:**
    - `include_failed` - Include failed conversions (default: true)
    - `include_skipped` - Include skipped files (default: false)
    
    **Use cases:**
    - Reviewing conversion quality
    - Debugging conversion failures
    - Getting output file paths
    - Performance analysis
    
    Useful for post-conversion review and troubleshooting.
    """
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=400,
                detail="task_id is required"
            )
        
        # Get conversion service
        service = get_conversion_service()
        
        # Get task status with results
        status = await service.get_task_status(task_id)
        
        if not status:
            logger.warning(f"Conversion task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Conversion task not found: {task_id}"
            )
        
        # Filter results based on parameters
        results = status.get('results', [])
        
        if not include_failed:
            results = [r for r in results if r.status == ConversionStatus.COMPLETED]
        
        if not include_skipped:
            results = [r for r in results if r.status != ConversionStatus.COMPLETED or r.filename]
        
        # Update status with filtered results
        status['results'] = results
        
        return ConversionStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversion results: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get results: {str(e)}"
        )


@router.post("/validate", response_model=SuccessResponse)
async def validate_documents(
    input_dir: Optional[str] = None,
    check_formats: bool = True,
    check_size: bool = True,
    max_size_mb: Optional[int] = None
):
    """
    Validate documents before conversion.
    
    **Pre-flight checks:**
    - File format is supported
    - File size within limits
    - File is readable and not corrupted
    - Directory structure is valid
    
    **Parameters:**
    - `input_dir` - Directory to validate (uses config default if not provided)
    - `check_formats` - Validate file formats (default: true)
    - `check_size` - Validate file sizes (default: true)
    - `max_size_mb` - Custom size limit (uses config default if not provided)
    
    **Returns validation report:**
    - Valid files count
    - Invalid files with reasons
    - Size violations
    - Format violations
    
    **Example:**
    ```json
    {
      "input_dir": "./data/raw",
      "check_formats": true,
      "check_size": true,
      "max_size_mb": 50
    }
    ```
    
    Returns validation results without starting conversion.
    Use before conversion to identify potential issues.
    """
    try:
        # Get conversion service
        service = get_conversion_service()
        
        # Validate documents
        validation_result = await service.validate_documents(
            input_dir=input_dir,
            check_formats=check_formats,
            check_size=check_size,
            max_size_mb=max_size_mb
        )
        
        if not validation_result.get('valid', False):
            # Return success response with warnings
            warnings = validation_result.get('warnings', [])
            errors = validation_result.get('errors', [])
            
            message = "Validation completed with issues"
            if errors:
                message = f"Validation failed: {'; '.join(errors[:3])}"
            elif warnings:
                message = f"Validation warnings: {'; '.join(warnings[:3])}"
            
            return SuccessResponse(
                success=False,
                message=message,
            )
        
        return SuccessResponse(
            success=True,
            message=f"All documents passed validation. {validation_result.get('supported_files', 0)} files ready for conversion.",
        )
        
    except Exception as e:
        logger.error(f"Failed to validate documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/retry", response_model=ConversionResponse, responses={404: {"model": ErrorResponse}})
async def retry_failed_conversions(
    task_id: str,
    background_tasks: BackgroundTasks
):
    """
    Retry failed conversions from a previous task.
    
    **Process:**
    1. Identifies files that failed in original task
    2. Attempts conversion again with same settings
    3. Creates new task for retry attempt
    
    **Parameters:**
    - `task_id` - Original task ID with failures
    
    **Use cases:**
    - Recovering from temporary failures
    - Retrying after fixing source files
    - Handling transient errors
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/conversion/retry?task_id=conv_abc123"
    ```
    
    Returns new task ID for tracking retry progress.
    Useful when conversion failed due to temporary issues.
    """
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=400,
                detail="task_id is required"
            )
        
        # Get conversion service
        service = get_conversion_service()
        
        # Retry failed conversions
        new_task_id = await service.retry_failed_conversions(task_id)
        
        if not new_task_id:
            logger.warning(f"No failed conversions to retry in task: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"No failed conversions found in task: {task_id}"
            )
        
        # Start retry in background
        background_tasks.add_task(
            service.start_conversion,
            task_id=new_task_id,
        )
        
        logger.info(f"Started retry conversion task: {new_task_id} for original task: {task_id}")
        
        # Get supported formats
        formats_info = await service.get_supported_formats()
        supported_formats = formats_info.get('formats', ["pdf", "docx", "pptx", "html", "png", "jpg"])
        
        return ConversionResponse(
            success=True,
            message=f"Retry conversion started for failed files from task {task_id}",
            task_id=new_task_id,
            files_to_convert=0,  # Will be updated during processing
            supported_formats=supported_formats,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry conversion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Retry failed: {str(e)}"
        )


@router.delete("/task/{task_id}", response_model=SuccessResponse, responses={404: {"model": ErrorResponse}})
async def delete_conversion_task(task_id: str):
    """
    Delete conversion task and its results.
    
    **Process:**
    - Removes task from memory/storage
    - Does NOT delete converted markdown files
    - Only removes task tracking data
    
    **Parameters:**
    - `task_id` - Task ID to delete
    
    **Note:** Converted markdown files remain in output directory.
    This only cleans up task tracking metadata.
    
    Use to clean up completed or failed tasks from memory.
    """
    try:
        if not task_id or not task_id.strip():
            raise HTTPException(
                status_code=400,
                detail="task_id is required"
            )
        
        # Get conversion service
        service = get_conversion_service()
        
        # Delete task
        success = await service.delete_task(task_id)
        
        if not success:
            logger.warning(f"Conversion task not found: {task_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Conversion task not found: {task_id}"
            )
        
        logger.info(f"Deleted conversion task: {task_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Conversion task {task_id} deleted successfully",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversion task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Delete failed: {str(e)}"
        )


@router.get("/history", response_model=List[ConversionStatusResponse])
async def get_conversion_history(limit: int = 10):
    """
    Get history of conversion tasks.
    
    **Returns:**
    - Past conversion runs
    - Success/failure status
    - Files processed
    - Processing time
    - Error summaries
    
    **Parameters:**
    - `limit` - Maximum tasks to return (1-100, default: 10)
    
    **Sorted by:** Most recent first
    
    **Use cases:**
    - Tracking conversion performance over time
    - Identifying recurring issues
    - Auditing conversion operations
    - Performance analysis
    
    Useful for monitoring conversion trends and quality.
    """
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )
        
        # Get conversion service
        service = get_conversion_service()
        
        # Get conversion history
        history = await service.get_conversion_history(limit=limit)
        
        logger.info(f"Retrieved {len(history)} conversion history items")
        
        # Convert history items to the expected ConversionStatusResponse format
        return [
            ConversionStatusResponse(
                task_id=item['task_id'],
                progress=ConversionProgress(
                    status=ConversionStatus(item['status']),
                    total_files=item['total_files'],
                    converted_files=item['converted_files'],
                    failed_files=item['failed_files'],
                    skipped_files=0,
                    progress_percentage=100.0,
                    current_file=None,
                    elapsed_time=item.get('duration', 0) or 0,
                    estimated_remaining=None,
                ),
                results=[],  # Results are not typically needed for history view
            ) for item in history
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversion history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get history: {str(e)}"
        )