#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# api/core/task_cleanup.py
# Automatic cleanup of completed tasks to prevent memory leaks

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class TaskCleanupManager:
    """
    Manager for automatic cleanup of completed tasks
    
    Prevents memory leaks by:
    - Removing old completed tasks
    - Cleaning up failed tasks after retention period
    - Limiting total task history
    """
    
    def __init__(
        self,
        cleanup_interval_seconds: int = 300,  # 5 minutes
        completed_task_retention_hours: int = 24,  # Keep for 24 hours
        failed_task_retention_hours: int = 72,  # Keep failed tasks longer
        max_task_history: int = 100,  # Maximum tasks to keep in memory
    ):
        """
        Initialize task cleanup manager
        
        Args:
            cleanup_interval_seconds: How often to run cleanup (default: 5 min)
            completed_task_retention_hours: Hours to keep completed tasks (default: 24h)
            failed_task_retention_hours: Hours to keep failed tasks (default: 72h)
            max_task_history: Maximum tasks to keep regardless of age (default: 100)
        """
        self.cleanup_interval = cleanup_interval_seconds
        self.completed_retention = timedelta(hours=completed_task_retention_hours)
        self.failed_retention = timedelta(hours=failed_task_retention_hours)
        self.max_history = max_task_history
        
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.stats = {
            'total_cleanups': 0,
            'tasks_cleaned': 0,
            'last_cleanup': None,
            'next_cleanup': None,
        }
    
    async def start(self):
        """Start automatic cleanup background task"""
        if self._running:
            logger.warning("Task cleanup already running")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("✅ Task cleanup manager started")
        logger.info(f"   Cleanup interval: {self.cleanup_interval}s")
        logger.info(f"   Completed task retention: {self.completed_retention.total_seconds()/3600:.1f}h")
        logger.info(f"   Failed task retention: {self.failed_retention.total_seconds()/3600:.1f}h")
        logger.info(f"   Max task history: {self.max_history}")
    
    async def stop(self):
        """Stop automatic cleanup background task"""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Task cleanup manager stopped")
    
    async def _cleanup_loop(self):
        """Background loop that periodically cleans up tasks"""
        logger.info("🔄 Task cleanup loop started")
        
        while self._running:
            try:
                # Calculate next cleanup time
                next_cleanup = datetime.now() + timedelta(seconds=self.cleanup_interval)
                self.stats['next_cleanup'] = next_cleanup
                
                # Wait for cleanup interval
                await asyncio.sleep(self.cleanup_interval)
                
                # Perform cleanup
                await self._perform_cleanup()
                
            except asyncio.CancelledError:
                logger.info("Task cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _perform_cleanup(self):
        """Perform cleanup of old tasks"""
        logger.debug("🧹 Running task cleanup...")
        
        cleanup_start = datetime.now()
        total_cleaned = 0
        
        try:
            # Import services
            from api.modules.indexing.services.indexing_service import get_indexing_service
            from api.modules.indexing.services.conversion_service import get_conversion_service
            
            # Clean indexing tasks
            indexing_service = get_indexing_service()
            indexing_cleaned = await self._cleanup_indexing_tasks(indexing_service)
            total_cleaned += indexing_cleaned
            
            # Clean conversion tasks
            conversion_service = get_conversion_service()
            conversion_cleaned = await self._cleanup_conversion_tasks(conversion_service)
            total_cleaned += conversion_cleaned
            
            # Update stats
            self.stats['total_cleanups'] += 1
            self.stats['tasks_cleaned'] += total_cleaned
            self.stats['last_cleanup'] = cleanup_start
            
            if total_cleaned > 0:
                logger.info(f"✅ Cleanup completed: {total_cleaned} tasks removed")
            else:
                logger.debug("✅ Cleanup completed: no tasks to remove")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
    
    async def _cleanup_indexing_tasks(self, service) -> int:
        """
        Clean up old indexing tasks
        
        Args:
            service: IndexingService instance
        
        Returns:
            int: Number of tasks cleaned
        """
        try:
            cleaned = 0
            now = datetime.now()
            
            # Get all tasks
            all_tasks = await service.get_all_tasks()
            
            # Sort by start time (oldest first)
            all_tasks.sort(key=lambda t: t.get('start_time', now), reverse=False)
            
            # Keep only recent tasks if exceeds max history
            if len(all_tasks) > self.max_history:
                tasks_to_remove = len(all_tasks) - self.max_history
                logger.info(f"🧹 Indexing: Removing {tasks_to_remove} old tasks (max history exceeded)")
                
                for task_info in all_tasks[:tasks_to_remove]:
                    task_id = task_info.get('task_id')
                    if task_id:
                        task = await service.get_task(task_id)
                        if task:
                            # Remove from service internal storage
                            async with service._lock:
                                if task_id in service._tasks:
                                    del service._tasks[task_id]
                                    cleaned += 1
            
            # Remove old completed/failed tasks
            for task_info in all_tasks:
                task_id = task_info.get('task_id')
                status = task_info.get('status')
                end_time = task_info.get('end_time')
                
                if not task_id or not status or not end_time:
                    continue
                
                # Check if task is old enough to remove
                age = now - end_time
                
                should_remove = False
                
                if status == 'completed' and age > self.completed_retention:
                    should_remove = True
                elif status in ['failed', 'cancelled'] and age > self.failed_retention:
                    should_remove = True
                
                if should_remove:
                    async with service._lock:
                        if task_id in service._tasks:
                            del service._tasks[task_id]
                            cleaned += 1
                            logger.debug(f"   Removed indexing task {task_id} (status: {status}, age: {age.total_seconds()/3600:.1f}h)")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup indexing tasks: {e}")
            return 0
    
    async def _cleanup_conversion_tasks(self, service) -> int:
        """
        Clean up old conversion tasks
        
        Args:
            service: ConversionService instance
        
        Returns:
            int: Number of tasks cleaned
        """
        try:
            cleaned = 0
            now = datetime.now()
            
            # Get all tasks from service
            async with service._lock:
                all_task_ids = list(service._tasks.keys())
            
            # Sort tasks by end time
            tasks_with_times = []
            for task_id in all_task_ids:
                task = await service.get_task(task_id)
                if task and task.end_time:
                    tasks_with_times.append((task_id, task))
            
            tasks_with_times.sort(key=lambda t: t[1].end_time, reverse=False)
            
            # Keep only recent tasks if exceeds max history
            if len(tasks_with_times) > self.max_history:
                tasks_to_remove = len(tasks_with_times) - self.max_history
                logger.info(f"🧹 Conversion: Removing {tasks_to_remove} old tasks (max history exceeded)")
                
                for task_id, task in tasks_with_times[:tasks_to_remove]:
                    async with service._lock:
                        if task_id in service._tasks:
                            del service._tasks[task_id]
                            cleaned += 1
            
            # Remove old completed/failed tasks
            for task_id, task in tasks_with_times:
                if not task.end_time:
                    continue
                
                age = now - task.end_time
                should_remove = False
                
                if task.status.value == 'completed' and age > self.completed_retention:
                    should_remove = True
                elif task.status.value == 'failed' and age > self.failed_retention:
                    should_remove = True
                
                if should_remove:
                    async with service._lock:
                        if task_id in service._tasks:
                            del service._tasks[task_id]
                            cleaned += 1
                            logger.debug(f"   Removed conversion task {task_id} (status: {task.status.value}, age: {age.total_seconds()/3600:.1f}h)")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup conversion tasks: {e}")
            return 0
    
    async def manual_cleanup(self) -> dict:
        """
        Manually trigger cleanup (useful for testing or forced cleanup)
        
        Returns:
            dict: Cleanup results
        """
        logger.info("🧹 Manual cleanup triggered")
        
        cleanup_start = datetime.now()
        
        await self._perform_cleanup()
        
        cleanup_time = (datetime.now() - cleanup_start).total_seconds()
        
        return {
            'success': True,
            'cleanup_time': cleanup_time,
            'tasks_cleaned': self.stats['tasks_cleaned'],
            'timestamp': datetime.now()
        }
    
    def get_stats(self) -> dict:
        """Get cleanup statistics"""
        return {
            **self.stats,
            'running': self._running,
            'cleanup_interval': self.cleanup_interval,
            'completed_retention_hours': self.completed_retention.total_seconds() / 3600,
            'failed_retention_hours': self.failed_retention.total_seconds() / 3600,
            'max_history': self.max_history,
        }


# Global cleanup manager instance
_cleanup_manager: Optional[TaskCleanupManager] = None


def get_cleanup_manager() -> TaskCleanupManager:
    """Get or create global cleanup manager"""
    global _cleanup_manager
    
    if _cleanup_manager is None:
        # Create with default settings or from environment
        import os
        
        cleanup_interval = int(os.getenv("TASK_CLEANUP_INTERVAL", "300"))  # 5 minutes
        completed_retention = int(os.getenv("COMPLETED_TASK_RETENTION_HOURS", "24"))
        failed_retention = int(os.getenv("FAILED_TASK_RETENTION_HOURS", "72"))
        max_history = int(os.getenv("MAX_TASK_HISTORY", "100"))
        
        _cleanup_manager = TaskCleanupManager(
            cleanup_interval_seconds=cleanup_interval,
            completed_task_retention_hours=completed_retention,
            failed_task_retention_hours=failed_retention,
            max_task_history=max_history,
        )
    
    return _cleanup_manager


async def start_task_cleanup():
    """Start automatic task cleanup (call in lifespan startup)"""
    manager = get_cleanup_manager()
    await manager.start()


async def stop_task_cleanup():
    """Stop automatic task cleanup (call in lifespan shutdown)"""
    manager = get_cleanup_manager()
    await manager.stop()