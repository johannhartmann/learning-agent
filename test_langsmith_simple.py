#!/usr/bin/env python
"""Simple test to verify LangSmith integration with the new architecture."""

import asyncio
import os

from langsmith import Client

from learning_agent.learning_supervisor import LearningSupervisor


async def main() -> None:
    """Run a simple test with LangSmith tracing."""
    print("LangSmith Integration Test")
    print("=" * 60)

    # Check configuration
    print("\nConfiguration:")
    print(f"  LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
    print(f"  LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
    print(f"  LANGSMITH_API_KEY: {'Set' if os.getenv('LANGSMITH_API_KEY') else 'Not set'}")

    # Test LangSmith client
    try:
        client = Client()
        datasets = list(client.list_datasets(limit=3))
        print(f"\n✓ LangSmith client connected, found {len(datasets)} datasets")
    except Exception as e:
        print(f"\n✗ LangSmith client error: {e}")
        return

    # Test LearningSupervisor with tracing
    print("\nRunning test tasks with tracing...")
    print("-" * 40)

    supervisor = LearningSupervisor()

    test_tasks = [
        "Say hello",
        "Count to 5",
        "List 3 programming languages",
    ]

    for i, task in enumerate(test_tasks, 1):
        print(f"\nTask {i}: {task}")
        try:
            result = await supervisor.process_task(task)
            print(f"  Status: {result.get('status')}")
            print(f"  Duration: {result.get('duration', 0):.2f}s")

            # Extract a snippet of the summary
            summary = result.get("summary", "No summary")
            if len(summary) > 100:
                summary = summary[:100] + "..."
            print(f"  Summary: {summary}")
        except Exception as e:
            print(f"  Error: {e}")

    await supervisor.shutdown()

    print("\n" + "=" * 60)
    print("✓ Test completed!")
    print("\nView traces at: https://smith.langchain.com")
    print(f"Project: {os.getenv('LANGSMITH_PROJECT', 'learning-agent')}")


if __name__ == "__main__":
    asyncio.run(main())
