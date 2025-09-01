#!/usr/bin/env python3
"""Test script to verify matplotlib sandbox functionality."""

import asyncio
import sys
from pathlib import Path


# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from learning_agent.tools.sandbox_tool import get_sandbox


async def test_matplotlib():
    """Test matplotlib functionality in sandbox."""
    print("Testing matplotlib in sandbox...")

    sandbox = await get_sandbox()

    code = """
import numpy as np
import matplotlib.pyplot as plt

# Generate data
x = np.linspace(0, 2 * np.pi, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', label='sin(x)')
plt.title('Simple Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.legend()
plt.show()

print("Plot created successfully!")
"""

    try:
        result = await sandbox.execute_with_viz(code)
        print(f"Execution successful: {result.get('success', False)}")
        print(f"Stdout: {result.get('stdout', '')}")
        print(f"Stderr: {result.get('stderr', '')}")
        print(f"Images: {len(result.get('images', []))} found")

        if result.get("images"):
            for i, img in enumerate(result["images"]):
                print(
                    f"  Image {i + 1}: {img['type']}, {img['format']}, {len(img['base64'])} chars"
                )

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_matplotlib())
