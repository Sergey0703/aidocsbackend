#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/routes/monitoring.py
# Real implementation with MonitoringService integration

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime, timedelta

from ..models.schemas import (
    PipelineStatusResponse,
    PerformanceMetricsResponse,
    ErrorLogResponse,
    ProcessingQueueResponse,
    ChunkAnalysisResponse,
    DatabaseStatsResponse,
    ErrorLogItem,
    ProcessingQueueItem,
    PipelineStageMetrics,
    ErrorResponse,
)
from ..services.monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pipeline", response_model=PipelineStatusResponse)
async def get_pipeline_status(task_id: Optional[str] = None):
    """
    Get detailed pipeline status.
    
    **Returns status for each processing stage:**
    - Document Conversion (Part 1)
    - Document Loading
    - Chunking
    - Embedding Generation
    - Database Saving
    
    **Shows:**
    - Current stage
    - Progress per stage
    - Time spent in each stage
    - Errors per stage
    
    **Parameters:**
    - `task_id` - Specific task ID (optional, uses latest if not provided)
    
    **Example response:**
    ```json
    {
      "overall_status": "running",
      "current_stage": "embedding",
      "stages": [
        {
          "stage_name": "Loading",
          "status": "completed",
          "progress_percentage": 100.0
        }
      ],
      "overall_progress": 65.0
    }
    ```
    
    Use for real-time monitoring of indexing pipeline.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get pipeline status
        status = await service.get_pipeline_status(task_id=task_id)
        
        return PipelineStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline status: {str(e)}"
        )


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(task_id: Optional[str] = None):
    """
    Get detailed performance metrics.
    
    **Returns:**
    - Processing speed (chunks/second)
    - Average time per file/chunk
    - Resource usage (memory, CPU)
    - Gemini API metrics:
      - API calls made
      - Calls per minute
      - Rate limit hits
      - API errors
    - Processing efficiency
    
    **Parameters:**
    - `task_id` - Specific task ID (optional)
    
    **Metrics breakdown:**
    - `current_speed` - Current processing rate
    - `average_speed` - Overall average rate
    - `peak_speed` - Maximum observed rate
    - `api_calls_per_minute` - Gemini API usage rate
    - `processing_efficiency` - Success rate percentage
    
    **Use cases:**
    - Performance optimization
    - Capacity planning
    - Bottleneck identification
    - Cost analysis (API usage)
    
    Useful for optimization and capacity planning.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get performance metrics
        metrics = await service.get_performance_metrics(task_id=task_id)
        
        return PerformanceMetricsResponse(**metrics)
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/errors", response_model=ErrorLogResponse)
async def get_error_logs(
    limit: int = 50,
    error_type: Optional[str] = None,
    since: Optional[datetime] = None
):
    """
    Get error logs from indexing process.
    
    **Returns:**
    - Error timestamp
    - Error type (conversion, chunking, embedding, database)
    - Error message
    - Affected file
    - Processing stage
    
    **Filters:**
    - `limit` - Maximum errors to return (1-500, default: 50)
    - `error_type` - Filter by error type (optional)
    - `since` - Filter by date (default: last 7 days)
    
    **Error types:**
    - `conversion_error` - Document conversion failures
    - `chunking_error` - Text chunking issues
    - `embedding_error` - Gemini API failures
    - `database_error` - Vector store issues
    - `validation_error` - Content validation failures
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/monitoring/errors?limit=20&error_type=embedding_error"
    ```
    
    Useful for debugging and identifying systematic issues.
    """
    try:
        if limit < 1 or limit > 500:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 500"
            )
        
        # Default to last 7 days if not specified
        if since is None:
            since = datetime.now() - timedelta(days=7)
        
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get error logs
        errors, total_errors, error_types, most_recent_error = await service.get_error_logs(
            limit=limit,
            error_type=error_type,
            since=since
        )
        
        logger.info(f"Retrieved {len(errors)} error logs")
        
        return ErrorLogResponse(
            errors=errors,
            total_errors=total_errors,
            error_types=error_types,
            most_recent_error=most_recent_error,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get error logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get error logs: {str(e)}"
        )


@router.get("/queue", response_model=ProcessingQueueResponse)
async def get_processing_queue():
    """
    Get current processing queue.
    
    **Shows:**
    - Files waiting to be processed
    - Current file being processed
    - Position in queue
    - Estimated start time for each file
    - Estimated completion time
    
    **Queue information:**
    - `queue_length` - Number of files waiting
    - `processing_now` - Currently processing file
    - `estimated_completion` - When queue will be empty
    
    **Use cases:**
    - Monitoring batch processing progress
    - Estimating wait times
    - Identifying bottlenecks
    - Queue management
    
    Useful for monitoring batch processing progress.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get processing queue
        queue_info = await service.get_processing_queue()
        
        return ProcessingQueueResponse(**queue_info)
        
    except Exception as e:
        logger.error(f"Failed to get processing queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get processing queue: {str(e)}"
        )


@router.get("/chunks/analysis", response_model=ChunkAnalysisResponse)
async def get_chunk_analysis():
    """
    Get comprehensive chunk analysis.
    
    **Analyzes:**
    - Total chunks in database
    - Chunk size distribution (min, max, avg, median)
    - Chunks per file statistics
    - Quality distribution (excellent, good, moderate, poor)
    - Top files by chunk count
    
    **Quality categories:**
    - **Excellent:** > 1000 chars per chunk
    - **Good:** 500-1000 chars
    - **Moderate:** 200-500 chars
    - **Poor:** < 200 chars
    
    **Statistics:**
    - Size metrics (min, max, avg, median)
    - Distribution across files
    - Quality breakdown
    - Top contributors
    
    **Use cases:**
    - Data quality assessment
    - Chunk effectiveness evaluation
    - Configuration optimization
    - Identifying problematic documents
    
    Useful for understanding data quality and chunk effectiveness.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get chunk analysis
        analysis = await service.get_chunk_analysis()
        
        return ChunkAnalysisResponse(**analysis)
        
    except Exception as e:
        logger.error(f"Failed to get chunk analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chunk analysis: {str(e)}"
        )


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_stats():
    """
    Get database statistics.
    
    **Returns:**
    - Total records in database
    - Table size and index size
    - Vector dimension
    - Total vectors stored
    - Average query time
    - Connection status
    - Last backup timestamp
    
    **Database metrics:**
    - `total_records` - Number of vector records
    - `table_size_mb` - Storage used by table
    - `index_size_mb` - Storage used by indexes
    - `vector_dimension` - Embedding dimension (e.g., 768)
    - `total_vectors` - Count of non-null embeddings
    
    **Health indicators:**
    - Connection status
    - Query performance
    - Storage efficiency
    - Backup status
    
    **Use cases:**
    - Database health monitoring
    - Storage planning
    - Performance optimization
    - Backup verification
    
    Critical for monitoring database health and performance.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get database statistics
        stats = await service.get_database_stats()
        
        return DatabaseStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database stats: {str(e)}"
        )


@router.get("/health", response_model=dict)
async def health_check():
    """
    Quick health check for indexing system.
    
    **Returns:**
    - Overall system health status
    - Component availability:
      - Database connection
      - Gemini API access
      - File system access
    - Active tasks count
    - Recent errors count
    
    **Health status values:**
    - `healthy` - All systems operational
    - `degraded` - Some issues detected
    - `unhealthy` - Critical failures
    
    **Components checked:**
    - Database connectivity
    - Gemini API availability
    - File system access
    - Indexing service status
    
    **Response format:**
    ```json
    {
      "status": "healthy",
      "timestamp": "2024-01-01T12:00:00",
      "components": {
        "database": "operational",
        "gemini_api": "operational"
      },
      "active_tasks": 0,
      "recent_errors": 0
    }
    ```
    
    Lightweight endpoint for monitoring tools and health checks.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Perform health check
        health_status = await service.check_health()
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        # Return unhealthy status instead of raising exception
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "components": {},
            "active_tasks": 0,
            "recent_errors": 0
        }


@router.get("/metrics/summary", response_model=dict)
async def get_metrics_summary():
    """
    Get aggregated metrics summary.
    
    **Combines data from:**
    - Pipeline status
    - Performance metrics
    - Error logs
    - Database stats
    
    **Returns comprehensive overview:**
    - Pipeline state and progress
    - Processing performance
    - Data statistics
    - Error summary
    - Health indicators
    
    **Summary sections:**
    - **Pipeline:** Current status and progress
    - **Performance:** Speed and efficiency metrics
    - **Data:** Document and chunk counts
    - **Errors:** Error counts and types
    - **Health:** Overall system health
    
    **Example response:**
    ```json
    {
      "timestamp": "2024-01-01T12:00:00",
      "pipeline": {
        "status": "running",
        "progress": 75.0
      },
      "performance": {
        "processing_speed": 15.5,
        "efficiency": 98.2
      },
      "data": {
        "total_documents": 1000,
        "total_chunks": 50000
      },
      "errors": {
        "total": 5,
        "last_24h": 2
      },
      "health": {
        "overall": "healthy"
      }
    }
    ```
    
    Returns comprehensive overview in single response.
    Useful for dashboards and monitoring tools.
    """
    try:
        # Get monitoring service
        service = get_monitoring_service()
        
        # Get aggregated summary
        summary = await service.get_metrics_summary()
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get metrics summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics summary: {str(e)}"
        )