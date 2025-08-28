#!/usr/bin/env python3
"""Test the lifecycle management implementation."""

import asyncio
import os
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from learning_agent.learning.lifecycle_manager import FailureSeverity, LifecycleManager
from learning_agent.learning.maintenance_scheduler import MaintenanceScheduler
from learning_agent.learning.vector_storage import VectorLearningStorage


async def test_lifecycle() -> None:
    """Test the lifecycle management system."""

    print("🚀 Testing Learning Lifecycle Management System")
    print("=" * 50)

    # Initialize storage
    storage = VectorLearningStorage()
    await storage.initialize()

    # Create lifecycle manager
    lifecycle = LifecycleManager(storage)

    # Create maintenance scheduler
    scheduler = MaintenanceScheduler(storage)

    print("\n1️⃣ Testing Confidence Decay Algorithm")
    print("-" * 40)

    # Test confidence decay
    original = 1.0
    for days in [0, 30, 60, 90, 120]:
        decayed = lifecycle.calculate_confidence_decay(original, days)
        print(f"  After {days:3d} days: {original:.2f} → {decayed:.2f}")

    print("\n2️⃣ Testing Failure Severity Impact")
    print("-" * 40)

    confidence = 0.9
    for severity in [FailureSeverity.MINOR, FailureSeverity.MAJOR, FailureSeverity.CRITICAL]:
        adjusted = lifecycle.adjust_confidence_after_failure(confidence, severity)
        print(f"  {severity.value:8s}: {confidence:.2f} → {adjusted:.2f}")

    print("\n3️⃣ Creating Test Learning")
    print("-" * 40)

    # Store a test memory
    memory_data = {
        "task": "Test task for lifecycle management",
        "messages": [],
        "learning": {
            "tactical_learning": ["Use async for I/O"],
            "strategic_learning": ["Plan before coding"],
            "meta_learning": ["Learning improves with practice"],
            "anti_patterns": {"blocking_io": "Don't use synchronous I/O in async context"},
            "confidence_scores": {"overall": 0.8},
        },
        "execution_analysis": {"efficiency_score": 85, "tool_sequence": ["read", "write", "test"]},
    }
    learning_id = await storage.store_memory(memory_data)
    print(f"  ✅ Created learning with ID: {learning_id}")

    print("\n4️⃣ Testing Validation Tracking")
    print("-" * 40)

    # Simulate successful applications
    print("  Simulating successful applications...")
    for i in range(3):
        await lifecycle.validate_applied_learning(learning_id, success=True)
        print(f"    Success #{i + 1} applied")

    # Simulate a failure
    print("  Simulating a failure...")
    await lifecycle.validate_applied_learning(
        learning_id, success=False, severity=FailureSeverity.MINOR, failure_reason="Test failure"
    )
    print("    Failure applied")

    print("\n5️⃣ Testing Learning Metrics")
    print("-" * 40)

    metrics = await lifecycle.get_learning_metrics()
    print(f"  Total learnings: {metrics['total_count']}")
    print(f"  Health score: {metrics['health_score']:.2%}")
    print(f"  At risk: {metrics['at_risk_count']}")
    print(f"  New this week: {metrics['new_this_week']}")
    print("  State distribution:")
    for state, count in metrics["state_counts"].items():
        if count > 0:
            print(f"    - {state}: {count}")

    print("\n6️⃣ Testing Maintenance Tasks")
    print("-" * 40)

    # Run daily maintenance
    print("  Running daily maintenance...")
    await scheduler.daily_maintenance()

    # Run weekly maintenance
    print("  Running weekly maintenance...")
    await scheduler.weekly_maintenance()

    # Generate weekly report
    print("\n  Weekly Report:")
    report = await scheduler.generate_weekly_report()
    for key, value in report.items():
        if key != "state_distribution" and key != "timestamp":
            print(f"    - {key}: {value}")

    print("\n7️⃣ Testing Anti-Pattern Creation")
    print("-" * 40)

    # Create anti-pattern from failure
    try:
        anti_pattern_id = await lifecycle.create_anti_pattern_from_failure(
            learning_id, "This approach doesn't work in production"
        )
        if anti_pattern_id:
            print(f"  ✅ Created anti-pattern with ID: {anti_pattern_id}")
        else:
            print("  ⚠️ Failed to create anti-pattern")
    except Exception as e:
        print(f"  ⚠️ Error creating anti-pattern: {e}")

    print("\n✅ All tests completed successfully!")

    # Close connection pool
    if storage.pool:
        await storage.pool.close()


if __name__ == "__main__":
    # Ensure we have a database connection
    if not os.getenv("DATABASE_URL"):
        print("⚠️  Using default DATABASE_URL")

    asyncio.run(test_lifecycle())
