#!/usr/bin/env python
"""Demo script showing the Python sandbox tool in action."""

import asyncio
import os
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up environment
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from learning_agent.agent import create_learning_agent


async def demo_sandbox() -> None:
    """Demonstrate the sandbox tool functionality."""
    print("🚀 Learning Agent with Python Sandbox Demo")
    print("=" * 50)

    # Create the agent
    agent = create_learning_agent()

    # Test various sandbox capabilities
    tasks = [
        "Use the python sandbox to calculate the first 10 fibonacci numbers",
        "Use the python sandbox to create a simple plot of y = x^2 for x from -10 to 10",
        "Use the python sandbox to analyze this data: [1, 2, 3, 4, 5] - calculate mean, median, and standard deviation",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n📝 Task {i}: {task}")
        print("-" * 40)

        # Create state with the task
        state = {"messages": [{"role": "user", "content": task}]}

        # Run the agent
        result = await agent.ainvoke(state)  # type: ignore[attr-defined]

        # Display the last message (agent's response)
        if result.get("messages"):
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                print(f"✅ Response: {last_message.content[:500]}...")
            else:
                print(f"✅ Response: {str(last_message)[:500]}...")

        print()

    print("=" * 50)
    print("✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_sandbox())
