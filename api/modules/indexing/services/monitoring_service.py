#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/modules/indexing/services/monitoring_service.py
# Real implementation with metrics collection and analysis

import logging
import sys
import psutil
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from ..models.schemas import (
    IndexingStatus,
    ProcessingStage,
    PipelineStageMetrics,
    ErrorLogItem,
    ProcessingQueueItem,
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring indexing operations with real metrics"""
    
    def __init__(self):
        # Cache for metrics
        self._metrics_cache = {}
        self._cache_timeout = 10  # seconds
        
        logger.info("✅ MonitoringService initialized")
    
    def _setup_backend_path(self):
        """Add rag_indexer to Python path"""
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent.parent
            backend_path = project_root / "rag_indexer"
            
            if backend_path.exists():
                sys.path.insert(0, str(backend_path))
                logger.info(f"Added backend path: {backend_path}")
            else:
                logger.warning(f"Backend path not found: {backend_path}")
        except Exception as e:
            logger.error(f"Failed to setup backend path: {e}")
    
    def _get_config(self):
        """Get configuration"""
        try:
            # Add backend path to sys.path just-in-time
            self._setup_backend_path()
            
            from chunking_vectors.config import get_config
            return get_config()
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return None
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            # Add backend path to sys.path just-in-time
            self._setup_backend_path()
            
            import psycopg2
            config = self._get_config()
            if config:
                return psycopg2.connect(config.CONNECTION_STRING)
            return None
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            return None
    
    async def get_pipeline_status(
        self,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed pipeline status from active indexing task
        
        Returns:
            dict: Pipeline status with stage details
        """
        try:
            # Get active task from IndexingService if task_id provided
            if task_id:
                from .indexing_service import get_indexing_service
                
                indexing_service = get_indexing_service()
                task = await indexing_service.get_task(task_id)
                
                if task:
                    # Build stage metrics from task state
                    stages = []
                    
                    # Add completed stages
                    if task.statistics.documents_loaded > 0:
                        stages.append(PipelineStageMetrics(
                            stage_name="Document Loading",
                            status="completed",
                            progress_percentage=100.0,
                            items_processed=task.statistics.documents_loaded,
                            items_total=task.statistics.documents_loaded,
                            elapsed_time=0,
                            errors=0
                        ))
                    
                    if task.statistics.chunks_created > 0:
                        stages.append(PipelineStageMetrics(
                            stage_name="Chunking",
                            status="completed",
                            progress_percentage=100.0,
                            items_processed=task.statistics.chunks_created,
                            items_total=task.statistics.chunks_created,
                            elapsed_time=0,
                            errors=0
                        ))
                    
                    # Current stage
                    if task.stage:
                        current_stage_name = task.stage.value.replace('_', ' ').title()
                        stages.append(PipelineStageMetrics(
                            stage_name=current_stage_name,
                            status="running" if task.status == IndexingStatus.RUNNING else "completed",
                            progress_percentage=task.progress_percentage,
                            items_processed=task.processed_chunks,
                            items_total=task.total_chunks,
                            elapsed_time=(datetime.now() - task.start_time).total_seconds() if task.start_time else 0,
                            errors=len(task.errors)
                        ))
                    
                    return {
                        "overall_status": task.status,
                        "current_stage": task.stage,
                        "stages": stages,
                        "overall_progress": task.progress_percentage,
                    }
            
            # No active task - return idle state
            return {
                "overall_status": IndexingStatus.IDLE,
                "current_stage": None,
                "stages": [],
                "overall_progress": 0.0,
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}", exc_info=True)
            return {
                "overall_status": IndexingStatus.IDLE,
                "current_stage": None,
                "stages": [],
                "overall_progress": 0.0,
            }
    
    async def get_performance_metrics(
        self,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics from task or system
        
        Returns:
            dict: Performance metrics including speed, API usage, efficiency
        """
        try:
            metrics = {
                "current_speed": 0.0,
                "average_speed": 0.0,
                "peak_speed": 0.0,
                "total_processing_time": 0.0,
                "avg_time_per_file": 0.0,
                "avg_time_per_chunk": 0.0,
                "memory_usage_mb": None,
                "cpu_usage_percent": None,
                "api_calls": 0,
                "api_calls_per_minute": 0.0,
                "api_errors": 0,
                "api_rate_limit_hits": 0,
                "processing_efficiency": 0.0,
            }
            
            # Get task-specific metrics if task_id provided
            if task_id:
                from .indexing_service import get_indexing_service
                
                indexing_service = get_indexing_service()
                task = await indexing_service.get_task(task_id)
                
                if task:
                    metrics["current_speed"] = task.processing_speed
                    metrics["average_speed"] = task.processing_speed
                    metrics["avg_time_per_file"] = task.avg_time_per_file
                    
                    if task.start_time:
                        elapsed = (datetime.now() - task.start_time).total_seconds()
                        metrics["total_processing_time"] = elapsed
                        
                        if task.processed_chunks > 0 and elapsed > 0:
                            metrics["avg_time_per_chunk"] = elapsed / task.processed_chunks
                    
                    # API metrics from statistics
                    metrics["api_calls"] = task.statistics.gemini_api_calls
                    
                    if task.start_time and task.statistics.gemini_api_calls > 0:
                        elapsed_minutes = (datetime.now() - task.start_time).total_seconds() / 60
                        if elapsed_minutes > 0:
                            metrics["api_calls_per_minute"] = task.statistics.gemini_api_calls / elapsed_minutes
                    
                    # Efficiency
                    if task.total_chunks > 0:
                        metrics["processing_efficiency"] = (task.processed_chunks / task.total_chunks) * 100
            
            # System resource metrics
            try:
                process = psutil.Process()
                metrics["memory_usage_mb"] = process.memory_info().rss / 1024 / 1024
                metrics["cpu_usage_percent"] = process.cpu_percent(interval=0.1)
            except Exception as e:
                logger.warning(f"Failed to get system metrics: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}", exc_info=True)
            return {
                "current_speed": 0.0,
                "average_speed": 0.0,
                "peak_speed": 0.0,
                "total_processing_time": 0.0,
                "avg_time_per_file": 0.0,
                "avg_time_per_chunk": 0.0,
                "processing_efficiency": 0.0,
            }
    
    async def get_error_logs(
        self,
        limit: int = 50,
        error_type: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> tuple[List[ErrorLogItem], int, Dict[str, int], Optional[datetime]]:
        """
        Get error logs from log files and active tasks
        
        Returns:
            tuple: (errors, total_errors, error_types, most_recent_error)
        """
        try:
            errors = []
            error_types = {}
            most_recent_error = None
            
            # Set default time range
            if since is None:
                since = datetime.now() - timedelta(days=7)
            
            # Read from log files in rag_indexer/logs/
            log_dir = Path("rag_indexer/logs")
            
            if log_dir.exists():
                # Read error logs
                error_log_files = [
                    log_dir / "embedding_errors.log",
                    log_dir / "failed_chunks.log",
                    log_dir / "batch_failures.log",
                ]
                
                for log_file in error_log_files:
                    if log_file.exists():
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            # Parse log entries
                            # Format: "--- Stage at timestamp ---"
                            entries = content.split('---')
                            
                            for entry in entries:
                                if not entry.strip():
                                    continue
                                
                                lines = entry.strip().split('\n')
                                if len(lines) < 2:
                                    continue
                                
                                # Try to extract timestamp
                                header = lines[0]
                                timestamp_str = None
                                
                                # Look for timestamp in format "2024-01-01 12:00:00"
                                import re
                                timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', header)
                                if timestamp_match:
                                    timestamp_str = timestamp_match.group(0)
                                
                                if timestamp_str:
                                    try:
                                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                        
                                        if log_time < since:
                                            continue
                                        
                                        # Extract error info
                                        error_msg = '\n'.join(lines[1:])[:200]  # Limit length
                                        
                                        # Determine error type from filename
                                        error_type_name = log_file.stem.replace('_', ' ').title()
                                        
                                        # Create error log item
                                        error_item = ErrorLogItem(
                                            timestamp=log_time,
                                            error_type=error_type_name,
                                            error_message=error_msg,
                                            details={}
                                        )
                                        
                                        errors.append(error_item)
                                        
                                        # Update error types count
                                        error_types[error_type_name] = error_types.get(error_type_name, 0) + 1
                                        
                                        # Update most recent
                                        if most_recent_error is None or log_time > most_recent_error:
                                            most_recent_error = log_time
                                    
                                    except ValueError:
                                        continue
                        
                        except Exception as e:
                            logger.warning(f"Failed to read log file {log_file}: {e}")
            
            # Get errors from active tasks
            try:
                from .indexing_service import get_indexing_service
                
                indexing_service = get_indexing_service()
                all_tasks = await indexing_service.get_all_tasks()
                
                for task_info in all_tasks:
                    task = await indexing_service.get_task(task_info['task_id'])
                    if task and task.errors:
                        for error_msg in task.errors:
                            error_item = ErrorLogItem(
                                timestamp=task.start_time or datetime.now(),
                                error_type="Task Error",
                                error_message=error_msg,
                                details={"task_id": task.task_id}
                            )
                            errors.append(error_item)
                            error_types["Task Error"] = error_types.get("Task Error", 0) + 1
            
            except Exception as e:
                logger.warning(f"Failed to get task errors: {e}")
            
            # Sort by timestamp descending
            errors.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            errors = errors[:limit]
            
            return errors, len(errors), error_types, most_recent_error
            
        except Exception as e:
            logger.error(f"Failed to get error logs: {e}", exc_info=True)
            return [], 0, {}, None
    
    async def get_processing_queue(self) -> Dict[str, Any]:
        """
        Get current processing queue from active tasks
        
        Returns:
            dict: Queue information including files waiting and being processed
        """
        try:
            queue_items = []
            processing_now = None
            
            # Get active tasks
            from .indexing_service import get_indexing_service
            
            indexing_service = get_indexing_service()
            all_tasks = await indexing_service.get_all_tasks()
            
            for i, task_info in enumerate(all_tasks):
                task = await indexing_service.get_task(task_info['task_id'])
                
                if not task:
                    continue
                
                if task.status == IndexingStatus.RUNNING:
                    processing_now = task.current_file or f"Task {task.task_id[:8]}"
                elif task.status == IndexingStatus.IDLE:
                    # This task is in queue
                    queue_item = ProcessingQueueItem(
                        filename=f"Task {task.task_id[:8]}",
                        position=i + 1,
                        status="queued",
                        estimated_start_time=None
                    )
                    queue_items.append(queue_item)
            
            return {
                "queue": queue_items,
                "queue_length": len(queue_items),
                "processing_now": processing_now,
                "estimated_completion": None,
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing queue: {e}", exc_info=True)
            return {
                "queue": [],
                "queue_length": 0,
                "processing_now": None,
                "estimated_completion": None,
            }
    
    async def get_chunk_analysis(self) -> Dict[str, Any]:
        """
        Get comprehensive chunk analysis from database
        
        Returns:
            dict: Chunk statistics and quality distribution
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            config = self._get_config()
            cur = conn.cursor()
            
            # Total chunks and files
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT metadata->>'file_name') as total_files
                FROM vecs.{config.TABLE_NAME}
                WHERE metadata->>'file_name' IS NOT NULL
            """)
            
            total_chunks, total_files = cur.fetchone()
            
            # Chunk size statistics
            cur.execute(f"""
                SELECT 
                    MIN(LENGTH(metadata->>'text')) as min_size,
                    MAX(LENGTH(metadata->>'text')) as max_size,
                    AVG(LENGTH(metadata->>'text')) as avg_size,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(metadata->>'text')) as median_size
                FROM vecs.{config.TABLE_NAME}
                WHERE metadata->>'text' IS NOT NULL
            """)
            
            min_size, max_size, avg_size, median_size = cur.fetchone()
            
            # Chunks per file
            cur.execute(f"""
                SELECT 
                    metadata->>'file_name' as filename,
                    COUNT(*) as chunk_count
                FROM vecs.{config.TABLE_NAME}
                WHERE metadata->>'file_name' IS NOT NULL
                GROUP BY metadata->>'file_name'
                ORDER BY chunk_count DESC
                LIMIT 10
            """)
            
            top_files = [
                {"filename": row[0], "chunks": row[1]}
                for row in cur.fetchall()
            ]
            
            # Quality distribution based on chunk size
            cur.execute(f"""
                SELECT 
                    CASE 
                        WHEN LENGTH(metadata->>'text') > 1000 THEN 'excellent'
                        WHEN LENGTH(metadata->>'text') >= 500 THEN 'good'
                        WHEN LENGTH(metadata->>'text') >= 200 THEN 'moderate'
                        ELSE 'poor'
                    END as quality,
                    COUNT(*) as count
                FROM vecs.{config.TABLE_NAME}
                WHERE metadata->>'text' IS NOT NULL
                GROUP BY quality
            """)
            
            quality_distribution = {"excellent": 0, "good": 0, "moderate": 0, "poor": 0}
            for row in cur.fetchall():
                quality_distribution[row[0]] = row[1]
            
            cur.close()
            conn.close()
            
            analysis = {
                "total_chunks": total_chunks or 0,
                "total_files": total_files or 0,
                "avg_chunks_per_file": (total_chunks / total_files) if total_files > 0 else 0,
                "min_chunk_size": int(min_size) if min_size else 0,
                "max_chunk_size": int(max_size) if max_size else 0,
                "avg_chunk_size": float(avg_size) if avg_size else 0.0,
                "median_chunk_size": int(median_size) if median_size else 0,
                "top_files": top_files,
                "quality_distribution": quality_distribution
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to get chunk analysis: {e}", exc_info=True)
            return {
                "total_chunks": 0,
                "total_files": 0,
                "avg_chunks_per_file": 0.0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "avg_chunk_size": 0.0,
                "median_chunk_size": 0,
                "top_files": [],
                "quality_distribution": {"excellent": 0, "good": 0, "moderate": 0, "poor": 0}
            }
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            dict: Database statistics including size, records, performance
        """
        try:
            conn = self._get_db_connection()
            if not conn:
                raise Exception("Database connection failed")
            
            config = self._get_config()
            cur = conn.cursor()
            
            # Total records
            cur.execute(f"SELECT COUNT(*) FROM vecs.{config.TABLE_NAME}")
            total_records = cur.fetchone()[0]
            
            # Table and index sizes
            cur.execute(f"""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('vecs.{config.TABLE_NAME}')) as table_size,
                    pg_size_pretty(pg_indexes_size('vecs.{config.TABLE_NAME}')) as index_size,
                    pg_total_relation_size('vecs.{config.TABLE_NAME}') / (1024.0 * 1024.0) as table_size_mb,
                    pg_indexes_size('vecs.{config.TABLE_NAME}') / (1024.0 * 1024.0) as index_size_mb
            """)
            
            table_size, index_size, table_size_mb, index_size_mb = cur.fetchone()
            
            # Vector dimension (from first record)
            cur.execute(f"""
                SELECT array_length(embedding, 1) as dimension
                FROM vecs.{config.TABLE_NAME}
                WHERE embedding IS NOT NULL
                LIMIT 1
            """)
            
            result = cur.fetchone()
            vector_dimension = result[0] if result else 0
            
            # Total vectors (non-null embeddings)
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM vecs.{config.TABLE_NAME}
                WHERE embedding IS NOT NULL
            """)
            
            total_vectors = cur.fetchone()[0]
            
            # Connection status
            cur.execute("SELECT version()")
            pg_version = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            stats = {
                "total_records": total_records,
                "table_size_mb": float(table_size_mb),
                "index_size_mb": float(index_size_mb),
                "vector_dimension": vector_dimension,
                "total_vectors": total_vectors,
                "avg_query_time_ms": None,  # Would need query logging
                "connection_status": "operational",
                "last_backup": None,  # Would need backup system
                "database_version": pg_version.split()[0:2]  # PostgreSQL version
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}", exc_info=True)
            return {
                "total_records": 0,
                "table_size_mb": 0.0,
                "index_size_mb": 0.0,
                "vector_dimension": 0,
                "total_vectors": 0,
                "connection_status": "error",
            }
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform health check for indexing system
        
        Returns:
            dict: Health status of all components
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {},
                "active_tasks": 0,
                "recent_errors": 0
            }
            
            # Check database
            try:
                conn = self._get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    conn.close()
                    health_status["components"]["database"] = "operational"
                else:
                    health_status["components"]["database"] = "unavailable"
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["components"]["database"] = "error"
                health_status["status"] = "unhealthy"
                logger.error(f"Database health check failed: {e}")
            
            # Check Gemini API
            try:
                config = self._get_config()
                if config and config.GEMINI_API_KEY:
                    health_status["components"]["gemini_api"] = "configured"
                else:
                    health_status["components"]["gemini_api"] = "not_configured"
            except Exception as e:
                health_status["components"]["gemini_api"] = "error"
                logger.error(f"Gemini API check failed: {e}")
            
            # Check file system
            try:
                config = self._get_config()
                if config:
                    docs_dir = Path(config.DOCUMENTS_DIR)
                    if docs_dir.exists() and os.access(docs_dir, os.R_OK | os.W_OK):
                        health_status["components"]["file_system"] = "operational"
                    else:
                        health_status["components"]["file_system"] = "inaccessible"
                        health_status["status"] = "degraded"
            except Exception as e:
                health_status["components"]["file_system"] = "error"
                logger.error(f"File system check failed: {e}")
            
            # Check indexing service
            try:
                from .indexing_service import get_indexing_service
                indexing_service = get_indexing_service()
                active_count = indexing_service.get_active_tasks_count()
                health_status["active_tasks"] = active_count
                health_status["components"]["indexing_service"] = "operational"
            except Exception as e:
                health_status["components"]["indexing_service"] = "error"
                logger.error(f"Indexing service check failed: {e}")
            
            # Get recent errors count
            try:
                errors, total, _, _ = await self.get_error_logs(limit=100, since=datetime.now() - timedelta(hours=24))
                health_status["recent_errors"] = total
                
                if total > 10:
                    health_status["status"] = "degraded"
            except Exception as e:
                logger.error(f"Error count check failed: {e}")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get aggregated metrics summary
        
        Returns:
            dict: Comprehensive overview combining multiple metrics
        """
        try:
            # Get all metrics
            pipeline = await self.get_pipeline_status()
            performance = await self.get_performance_metrics()
            chunk_analysis = await self.get_chunk_analysis()
            db_stats = await self.get_database_stats()
            errors, error_count, error_types, _ = await self.get_error_logs(limit=100, since=datetime.now() - timedelta(hours=24))
            health = await self.check_health()
            
            summary = {
                "timestamp": datetime.now().isoformat(),
                "pipeline": {
                    "status": pipeline["overall_status"].value if hasattr(pipeline["overall_status"], 'value') else pipeline["overall_status"],
                    "progress": pipeline["overall_progress"],
                    "current_stage": pipeline["current_stage"].value if pipeline["current_stage"] and hasattr(pipeline["current_stage"], 'value') else None
                },
                "performance": {
                    "processing_speed": performance.get("current_speed", 0),
                    "efficiency": performance.get("processing_efficiency", 0),
                    "api_calls": performance.get("api_calls", 0)
                },
                "data": {
                    "total_documents": chunk_analysis["total_files"],
                    "total_chunks": chunk_analysis["total_chunks"],
                    "database_size_mb": db_stats["table_size_mb"]
                },
                "errors": {
                    "total": error_count,
                    "last_24h": error_count,
                    "by_type": error_types
                },
                "health": {
                    "overall": health["status"],
                    "database": health["components"].get("database", "unknown"),
                    "api": health["components"].get("gemini_api", "unknown")
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}", exc_info=True)
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }


# Singleton instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create monitoring service singleton"""
    global _monitoring_service
    
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    
    return _monitoring_service