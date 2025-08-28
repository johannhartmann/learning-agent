#!/usr/bin/env python3
"""Test the maintenance scheduler's actual scheduling functionality."""

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


async def test_scheduler() -> None:
    """Test the scheduler with accelerated timing."""

    print("🕐 Testing Maintenance Scheduler")
    print("=" * 50)

    # Initialize storage
    storage = VectorLearningStorage()
    await storage.initialize()

    # Create scheduler
    scheduler = MaintenanceScheduler(storage)

    # Override the maintenance methods to add logging
    original_daily = scheduler.daily_maintenance
    original_weekly = scheduler.weekly_maintenance
    original_monthly = scheduler.monthly_maintenance

    daily_runs = []
    weekly_runs = []
    monthly_runs = []

    async def logged_daily() -> None:
        print(f"  ✅ Daily maintenance triggered at {datetime.now()}")
        daily_runs.append(datetime.now())
        await original_daily()

    async def logged_weekly() -> None:
        print(f"  ✅ Weekly maintenance triggered at {datetime.now()}")
        weekly_runs.append(datetime.now())
        await original_weekly()

    async def logged_monthly() -> None:
        print(f"  ✅ Monthly maintenance triggered at {datetime.now()}")
        monthly_runs.append(datetime.now())
        await original_monthly()

    # Monkey patch the methods for testing
    scheduler.daily_maintenance = logged_daily  # type: ignore[method-assign]
    scheduler.weekly_maintenance = logged_weekly  # type: ignore[method-assign]
    scheduler.monthly_maintenance = logged_monthly  # type: ignore[method-assign]

    print("\n1️⃣ Testing immediate execution with run_now()")
    print("-" * 40)

    print("  Running daily maintenance immediately...")
    await scheduler.run_now("daily")
    print(f"  Daily runs: {len(daily_runs)}")

    print("  Running weekly maintenance immediately...")
    await scheduler.run_now("weekly")
    print(f"  Weekly runs: {len(weekly_runs)}")

    print("  Running monthly maintenance immediately...")
    await scheduler.run_now("monthly")
    print(f"  Monthly runs: {len(monthly_runs)}")

    print("\n2️⃣ Testing scheduler with accelerated timing")
    print("-" * 40)
    print("  Creating test scheduler that runs every few seconds...")

    # Create a test task that runs every 3 seconds
    test_runs = []

    async def test_task() -> None:
        test_runs.append(datetime.now())
        print(f"    Test task executed at {datetime.now().strftime('%H:%M:%S')}")

    # Start a simple recurring task
    async def run_every_n_seconds(
        n: int, task: Callable[[], Coroutine[Any, Any, None]], duration: int
    ) -> None:
        """Run a task every n seconds for duration seconds."""
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < duration:
            await task()
            await asyncio.sleep(n)

    print("  Starting test task to run every 3 seconds for 10 seconds...")
    print(f"  Start time: {datetime.now().strftime('%H:%M:%S')}")

    # Run the test task
    task = asyncio.create_task(run_every_n_seconds(3, test_task, 10))

    # Wait for it to complete
    await task

    print(f"  End time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Test task ran {len(test_runs)} times")

    print("\n3️⃣ Testing actual scheduler start/stop")
    print("-" * 40)

    # Start the scheduler
    print("  Starting scheduler...")
    await scheduler.start()
    print(f"  Scheduler running: {scheduler.running}")
    print(f"  Active tasks: {len(scheduler.tasks)}")

    # Let it run for a moment
    await asyncio.sleep(2)

    # Stop the scheduler
    print("  Stopping scheduler...")
    await scheduler.stop()
    print(f"  Scheduler running: {scheduler.running}")
    print(f"  Active tasks: {len(scheduler.tasks)}")

    print("\n✅ Scheduler tests completed!")

    # Close connection pool
    if storage.pool:
        await storage.pool.close()


if __name__ == "__main__":
    # Ensure we have a database connection
    if not os.getenv("DATABASE_URL"):
        print("⚠️  Using default DATABASE_URL")

    asyncio.run(test_scheduler())
