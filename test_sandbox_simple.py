#!/usr/bin/env python
"""Simple test of the sandbox without reset_state."""

import asyncio
import os
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up environment
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from learning_agent.tools.sandbox_tool import get_sandbox


async def test_simple_sandbox():
    """Test the sandbox with simple fibonacci calculation."""
    print("🧪 Testing Python Sandbox")
    print("=" * 50)

    sandbox = await get_sandbox()

    # Simple fibonacci calculation
    code = """
def fibonacci(n):
    sequence = [0, 1]
    while len(sequence) < n:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

# Calculate the first 10 Fibonacci numbers
result = fibonacci(10)
print("First 10 Fibonacci numbers:", result)
result
"""

    print("📝 Executing code...")
    result = await sandbox.execute_with_viz(code)

    print("\n✅ Result:")
    print(f"Success: {result['success']}")
    print(f"Output: {result['stdout']}")
    if result["stderr"]:
        print(f"Errors: {result['stderr']}")

    print("\n" + "=" * 50)
    print("✨ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_simple_sandbox())
