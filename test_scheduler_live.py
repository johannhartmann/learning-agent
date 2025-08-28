#!/usr/bin/env python3
"""Test scheduler with accelerated timing to verify cron-like behavior."""

import asyncio
import os
import sys
from collections.abc import Callable, Coroutine
from datetime import datetime
from pathlib import Path
from typing import Any


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from learning_agent.learning.maintenance_scheduler import MaintenanceScheduler
from learning_agent.learning.vector_storage import VectorLearningStorage


class AcceleratedScheduler(MaintenanceScheduler):
    """Scheduler with accelerated timing for testing."""

    def __init__(self, vector_storage: VectorLearningStorage):
        """Initialize with accelerated intervals."""
        super().__init__(vector_storage)
        self.daily_interval = 5  # 5 seconds instead of 24 hours
        self.weekly_interval = 15  # 15 seconds instead of 7 days
        self.monthly_interval = 30  # 30 seconds instead of 30 days
        self.daily_runs: list[datetime] = []
        self.weekly_runs: list[datetime] = []
        self.monthly_runs: list[datetime] = []

    async def daily_maintenance(self) -> None:
        """Override to track executions."""
        now = datetime.now()
        self.daily_runs.append(now)
        print(f"  ✅ Daily maintenance executed at {now.strftime('%H:%M:%S')}")

    async def weekly_maintenance(self) -> None:
        """Override to track executions."""
        now = datetime.now()
        self.weekly_runs.append(now)
        print(f"  ✅ Weekly maintenance executed at {now.strftime('%H:%M:%S')}")

    async def monthly_maintenance(self) -> None:
        """Override to track executions."""
        now = datetime.now()
        self.monthly_runs.append(now)
        print(f"  ✅ Monthly maintenance executed at {now.strftime('%H:%M:%S')}")

    async def run_accelerated_schedule(self, seconds: int) -> None:
        """Run accelerated schedule for specified seconds."""
        print(f"\n⏱️  Running accelerated schedule for {seconds} seconds")
        print(f"  Daily: every {self.daily_interval}s")
        print(f"  Weekly: every {self.weekly_interval}s")
        print(f"  Monthly: every {self.monthly_interval}s")
        print("-" * 40)

        # Create tasks for each schedule
        async def run_periodic(
            interval: int, task: Callable[[], Coroutine[Any, Any, None]]
        ) -> None:
            while True:
                await task()
                await asyncio.sleep(interval)

        tasks = [
            asyncio.create_task(run_periodic(self.daily_interval, self.daily_maintenance)),
            asyncio.create_task(run_periodic(self.weekly_interval, self.weekly_maintenance)),
            asyncio.create_task(run_periodic(self.monthly_interval, self.monthly_maintenance)),
        ]

        # Let them run for the specified duration
        await asyncio.sleep(seconds)

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        # Wait for cancellation to complete
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_accelerated_scheduler() -> None:
    """Test the scheduler with accelerated timing."""

    print("🕐 Testing Accelerated Maintenance Scheduler")
    print("=" * 50)

    # Initialize storage
    storage = VectorLearningStorage()
    await storage.initialize()

    # Create accelerated scheduler
    scheduler = AcceleratedScheduler(storage)

    # Run for 35 seconds to see multiple executions
    await scheduler.run_accelerated_schedule(35)

    print("\n📊 Execution Summary")
    print("-" * 40)
    print(f"  Daily runs ({scheduler.daily_interval}s interval): {len(scheduler.daily_runs)}")
    for i, run in enumerate(scheduler.daily_runs, 1):
        print(f"    {i}. {run.strftime('%H:%M:%S')}")

    print(f"\n  Weekly runs ({scheduler.weekly_interval}s interval): {len(scheduler.weekly_runs)}")
    for i, run in enumerate(scheduler.weekly_runs, 1):
        print(f"    {i}. {run.strftime('%H:%M:%S')}")

    print(
        f"\n  Monthly runs ({scheduler.monthly_interval}s interval): {len(scheduler.monthly_runs)}"
    )
    for i, run in enumerate(scheduler.monthly_runs, 1):
        print(f"    {i}. {run.strftime('%H:%M:%S')}")

    # Verify intervals
    print("\n🔍 Interval Verification")
    print("-" * 40)

    if len(scheduler.daily_runs) >= 2:
        daily_intervals = [
            (scheduler.daily_runs[i] - scheduler.daily_runs[i - 1]).total_seconds()
            for i in range(1, len(scheduler.daily_runs))
        ]
        avg_daily = sum(daily_intervals) / len(daily_intervals) if daily_intervals else 0
        print(f"  Average daily interval: {avg_daily:.1f}s (target: {scheduler.daily_interval}s)")

    if len(scheduler.weekly_runs) >= 2:
        weekly_intervals = [
            (scheduler.weekly_runs[i] - scheduler.weekly_runs[i - 1]).total_seconds()
            for i in range(1, len(scheduler.weekly_runs))
        ]
        avg_weekly = sum(weekly_intervals) / len(weekly_intervals) if weekly_intervals else 0
        print(
            f"  Average weekly interval: {avg_weekly:.1f}s (target: {scheduler.weekly_interval}s)"
        )

    if len(scheduler.monthly_runs) >= 2:
        monthly_intervals = [
            (scheduler.monthly_runs[i] - scheduler.monthly_runs[i - 1]).total_seconds()
            for i in range(1, len(scheduler.monthly_runs))
        ]
        avg_monthly = sum(monthly_intervals) / len(monthly_intervals) if monthly_intervals else 0
        print(
            f"  Average monthly interval: {avg_monthly:.1f}s (target: {scheduler.monthly_interval}s)"
        )

    print("\n✅ Accelerated scheduler test completed!")

    # Close connection pool
    if storage.pool:
        await storage.pool.close()


if __name__ == "__main__":
    # Ensure we have a database connection
    if not os.getenv("DATABASE_URL"):
        print("⚠️  Using default DATABASE_URL")

    asyncio.run(test_accelerated_scheduler())
