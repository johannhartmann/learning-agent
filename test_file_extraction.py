#!/usr/bin/env python3
"""Test file data extraction from sandbox."""

import asyncio

from learning_agent.tools.sandbox_tool import get_sandbox


async def test_file_extraction() -> None:
    """Test that file data is properly extracted."""

    # Test code that creates a matplotlib plot
    test_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(8, 6))
plt.plot(x, y, 'b-', label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Test Plot: sin(x)')
plt.legend()
plt.grid(True)

print("Plot created successfully!")
"""

    # Get sandbox and execute
    sandbox = await get_sandbox()
    result = await sandbox.execute_with_viz(test_code)

    print("=" * 60)
    print("EXECUTION RESULT")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Files: {result.get('files', [])}")

    # Check if files_data contains actual base64 data
    files_data = result.get("files_data", {})
    print(f"\nFiles data keys: {list(files_data.keys())}")

    for file_path, data in files_data.items():
        print(f"\nFile: {file_path}")
        print(f"Data length: {len(data)} chars")
        print(f"Data preview: {data[:100]}...")

        # Try to decode the base64 to verify it's valid
        import base64

        try:
            decoded = base64.b64decode(data)
            print(f"Decoded size: {len(decoded)} bytes")
            # Check PNG header
            if decoded[:8] == b"\x89PNG\r\n\x1a\n":
                print("✅ Valid PNG file detected")
            else:
                print(f"File header: {decoded[:8]}")
        except Exception as e:
            print(f"❌ Failed to decode: {e}")

    # Check if stdout contains the data marker
    if "__FILES_DATA__" in result.get("stdout", ""):
        print("\n⚠️ Files data marker still in stdout (should be cleaned)")
    else:
        print("\n✅ Files data marker properly removed from stdout")

    print(f"\nCleaned stdout: {result.get('stdout', '')}")


if __name__ == "__main__":
    asyncio.run(test_file_extraction())
