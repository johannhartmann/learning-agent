"""Scheduled maintenance tasks for learning system."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, time
from typing import Any

from learning_agent.learning.lifecycle_manager import LifecycleManager
from learning_agent.learning.pattern_generalizer import PatternGeneralizer
from learning_agent.learning.storage_optimizer import StorageOptimizer
from learning_agent.learning.vector_storage import VectorLearningStorage as VectorStorage


logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    """Schedules and runs maintenance tasks for the learning system."""

    def __init__(self, vector_storage: VectorStorage):
        """Initialize maintenance scheduler.

        Args:
            vector_storage: Vector storage instance
        """
        self.storage = vector_storage
        self.lifecycle_manager = LifecycleManager(vector_storage)
        self.pattern_generalizer = PatternGeneralizer(vector_storage)
        self.storage_optimizer = StorageOptimizer(vector_storage)
        self.running = False
        self.tasks: list[asyncio.Task[None]] = []

    async def daily_maintenance(self) -> None:
        """Daily maintenance tasks (run at 2 AM)."""
        logger.info("Starting daily maintenance")
        start_time = datetime.utcnow()

        try:
            # Apply confidence decay
            decay_count = await self.lifecycle_manager.apply_confidence_decay()
            logger.info(f"Applied confidence decay to {decay_count} learnings")

            # Transition declining learnings
            transition_count = await self.lifecycle_manager.transition_declining_learnings()
            logger.info(f"Transitioned {transition_count} learnings to declining")

            # Clean up failed learnings
            cleanup_count = await self.lifecycle_manager.cleanup_failed_learnings()
            logger.info(f"Cleaned up {cleanup_count} failed learnings")

            # Get and log metrics
            metrics = await self.lifecycle_manager.get_learning_metrics()
            logger.info(
                f"Learning health: {metrics['health_score']:.2%}, "
                f"At risk: {metrics['at_risk_count']}, "
                f"New this week: {metrics['new_this_week']}"
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Daily maintenance completed in {duration:.2f} seconds")

        except Exception as e:
            logger.error(f"Error in daily maintenance: {e}", exc_info=True)

    async def weekly_maintenance(self) -> None:
        """Weekly maintenance tasks (run Sunday at 3 AM)."""
        logger.info("Starting weekly maintenance")
        start_time = datetime.utcnow()

        try:
            # Find generalizable patterns
            generalized_count = await self.pattern_generalizer.find_generalizable_patterns()
            logger.info(f"Generalized {generalized_count} patterns")

            # Archive old learnings
            archive_count = await self.lifecycle_manager.archive_old_learnings()
            logger.info(f"Archived {archive_count} old learnings")

            # Merge duplicates
            merge_count = await self.storage_optimizer.merge_duplicate_learnings()
            logger.info(f"Merged {merge_count} duplicate learnings")

            # Generate weekly report
            report = await self.generate_weekly_report()
            logger.info(f"Weekly report: {report}")

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Weekly maintenance completed in {duration:.2f} seconds")

        except Exception as e:
            logger.error(f"Error in weekly maintenance: {e}", exc_info=True)

    async def monthly_maintenance(self) -> None:
        """Monthly maintenance tasks (run 1st Sunday at 4 AM)."""
        logger.info("Starting monthly maintenance")
        start_time = datetime.utcnow()

        try:
            # Backup before major operations
            backup_path = await self.storage_optimizer.backup_learnings()
            logger.info(f"Created backup at {backup_path}")

            # Storage optimization
            optimization_stats = await self.storage_optimizer.optimize_storage()
            logger.info(f"Storage optimization: {optimization_stats}")

            # Prune archived learnings
            prune_count = await self.lifecycle_manager.prune_archived_learnings()
            logger.info(f"Pruned {prune_count} archived learnings")

            # Compress old embeddings
            compress_count = await self.storage_optimizer.compress_old_embeddings()
            logger.info(f"Compressed {compress_count} old embeddings")

            # Deep pattern analysis
            pattern_insights = await self.pattern_generalizer.analyze_pattern_trends()
            logger.info(f"Pattern trends: {pattern_insights}")

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Monthly maintenance completed in {duration:.2f} seconds")

        except Exception as e:
            logger.error(f"Error in monthly maintenance: {e}", exc_info=True)

    async def generate_weekly_report(self) -> dict[str, Any]:
        """Generate weekly learning report.

        Returns:
            Dictionary with weekly statistics
        """
        metrics = await self.lifecycle_manager.get_learning_metrics()

        # Calculate week-over-week changes
        # In production, this would compare with stored previous week metrics
        report = {
            "total_learnings": metrics["total_count"],
            "health_score": metrics["health_score"],
            "new_learnings": metrics["new_this_week"],
            "at_risk_learnings": metrics["at_risk_count"],
            "state_distribution": metrics["state_counts"],
            "timestamp": datetime.utcnow().isoformat(),
        }

        return report

    async def run_at_time(
        self,
        target_hour: int,
        target_minute: int,
        task: Callable[[], Coroutine[Any, Any, None]],
        task_name: str,
    ) -> None:
        """Run a task at a specific time each day.

        Args:
            target_hour: Hour to run (0-23)
            target_minute: Minute to run (0-59)
            task: Async function to run
            task_name: Name for logging
        """
        while self.running:
            now = datetime.now()
            target_time = now.replace(
                hour=target_hour, minute=target_minute, second=0, microsecond=0
            )

            # If target time has passed today, schedule for tomorrow
            if target_time <= now:
                target_time = target_time.replace(day=target_time.day + 1)

            wait_seconds = (target_time - now).total_seconds()
            logger.info(
                f"Scheduled {task_name} to run at {target_time} ({wait_seconds / 3600:.1f} hours)"
            )

            await asyncio.sleep(wait_seconds)

            if self.running:
                logger.info(f"Running scheduled task: {task_name}")
                await task()

    async def run_weekly_at_time(
        self,
        target_weekday: int,  # 0=Monday, 6=Sunday
        target_hour: int,
        target_minute: int,
        task: Callable[[], Coroutine[Any, Any, None]],
        task_name: str,
    ) -> None:
        """Run a task weekly at a specific day and time.

        Args:
            target_weekday: Day of week (0=Monday, 6=Sunday)
            target_hour: Hour to run (0-23)
            target_minute: Minute to run (0-59)
            task: Async function to run
            task_name: Name for logging
        """
        while self.running:
            now = datetime.now()
            days_ahead = target_weekday - now.weekday()

            if days_ahead < 0:  # Target day already passed this week
                days_ahead += 7
            elif days_ahead == 0:  # Target day is today
                target_time = now.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )
                if target_time <= now:  # Time has passed today
                    days_ahead = 7

            target_date = now.date()
            if days_ahead > 0:
                target_date = now.date().replace(day=now.day + days_ahead)

            target_datetime = datetime.combine(target_date, time(target_hour, target_minute))

            wait_seconds = (target_datetime - now).total_seconds()
            logger.info(
                f"Scheduled {task_name} to run at {target_datetime} "
                f"({wait_seconds / 3600:.1f} hours)"
            )

            await asyncio.sleep(wait_seconds)

            if self.running:
                logger.info(f"Running scheduled task: {task_name}")
                await task()

    async def start(self) -> None:
        """Start the maintenance scheduler."""
        if self.running:
            logger.warning("Maintenance scheduler already running")
            return

        self.running = True
        logger.info("Starting maintenance scheduler")

        # Schedule daily tasks (2 AM)
        daily_task = asyncio.create_task(
            self.run_at_time(2, 0, self.daily_maintenance, "daily_maintenance")
        )
        self.tasks.append(daily_task)

        # Schedule weekly tasks (Sunday 3 AM)
        weekly_task = asyncio.create_task(
            self.run_weekly_at_time(6, 3, 0, self.weekly_maintenance, "weekly_maintenance")
        )
        self.tasks.append(weekly_task)

        # Schedule monthly tasks (1st Sunday 4 AM)
        # For simplicity, we'll run this on the 1st of each month at 4 AM
        monthly_task = asyncio.create_task(
            self.run_monthly_on_first(4, 0, self.monthly_maintenance, "monthly_maintenance")
        )
        self.tasks.append(monthly_task)

        logger.info("Maintenance scheduler started with 3 scheduled tasks")

    async def run_monthly_on_first(
        self,
        target_hour: int,
        target_minute: int,
        task: Callable[[], Coroutine[Any, Any, None]],
        task_name: str,
    ) -> None:
        """Run a task on the first day of each month.

        Args:
            target_hour: Hour to run (0-23)
            target_minute: Minute to run (0-59)
            task: Async function to run
            task_name: Name for logging
        """
        while self.running:
            now = datetime.now()

            # Calculate next first of month
            if now.day == 1:
                target_time = now.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )
                if target_time <= now:
                    # Time has passed, schedule for next month
                    if now.month == 12:
                        target_date = now.replace(year=now.year + 1, month=1, day=1)
                    else:
                        target_date = now.replace(month=now.month + 1, day=1)
                    target_time = target_date.replace(
                        hour=target_hour, minute=target_minute, second=0, microsecond=0
                    )
            else:
                # Schedule for next month's first day
                if now.month == 12:
                    target_date = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    target_date = now.replace(month=now.month + 1, day=1)
                target_time = target_date.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )

            wait_seconds = (target_time - now).total_seconds()
            logger.info(
                f"Scheduled {task_name} to run at {target_time} ({wait_seconds / 86400:.1f} days)"
            )

            await asyncio.sleep(wait_seconds)

            if self.running:
                logger.info(f"Running scheduled task: {task_name}")
                await task()

    async def stop(self) -> None:
        """Stop the maintenance scheduler."""
        logger.info("Stopping maintenance scheduler")
        self.running = False

        # Cancel all scheduled tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete cancellation
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        logger.info("Maintenance scheduler stopped")

    async def run_now(self, maintenance_type: str = "daily") -> None:
        """Run maintenance tasks immediately (for testing).

        Args:
            maintenance_type: Type of maintenance to run (daily, weekly, monthly)
        """
        if maintenance_type == "daily":
            await self.daily_maintenance()
        elif maintenance_type == "weekly":
            await self.weekly_maintenance()
        elif maintenance_type == "monthly":
            await self.monthly_maintenance()
        else:
            logger.error(f"Unknown maintenance type: {maintenance_type}")
