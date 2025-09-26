#!/usr/bin/env python3
"""Test matplotlib visualization in the frontend."""

import asyncio

from learning_agent.tools.sandbox_tool import get_sandbox


async def test_matplotlib() -> None:
    """Test that matplotlib plots are saved and tracked."""

    # Test code that creates a matplotlib plot
    test_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create some sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create a plot
plt.figure(figsize=(8, 6))
plt.plot(x, y, 'b-', label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Test Plot: sin(x)')
plt.legend()
plt.grid(True)

# Save the plot to see file tracking
plt.savefig('/tmp/test_plot.png')
print("Plot saved to /tmp/test_plot.png")

print("Plot created successfully!")
"""

    # Get the sandbox instance
    sandbox = await get_sandbox()

    # Execute the code
    result = await sandbox.execute_with_viz(test_code)

    print("Test completed!")
    print(f"Success: {result['success']}")
    print(f"Stdout: {result['stdout']}")
    if result["stderr"]:
        print(f"Stderr: {result['stderr']}")

    # Check if files were created
    if result.get("files"):
        print(f"Files created: {result['files']}")
    else:
        print("No files were tracked")


if __name__ == "__main__":
    asyncio.run(test_matplotlib())
