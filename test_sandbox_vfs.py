#!/usr/bin/env python
"""Test sandbox virtual filesystem."""

import asyncio
import sys


sys.path.insert(0, "/data/src/ml/learning_agent/src")

from learning_agent.tools.sandbox_tool import EnhancedSandbox


async def test_vfs():
    """Test virtual filesystem tracking."""

    sandbox = EnhancedSandbox(allow_network=False)

    # Test code that saves a file
    test_code = """
# Create a simple text file first
with open('/tmp/test.txt', 'w') as f:
    f.write('Hello World')
print("Created /tmp/test.txt")
"""

    raw_result = await sandbox.sandbox.execute(test_code)
    print("Result attributes:")
    for attr in dir(raw_result):
        if not attr.startswith("_"):
            value = getattr(raw_result, attr)
            if not callable(value):
                print(f"  {attr}: {value}")

    # Try get_file method
    if hasattr(raw_result, "get_file"):
        try:
            file_content = raw_result.get_file("/tmp/test.txt")
            print(f"\nget_file('/tmp/test.txt'): {file_content}")
        except Exception as e:
            print(f"\nget_file error: {e}")

    # Try save_files method
    if hasattr(raw_result, "save_files"):
        print(f"\nsave_files: {raw_result.save_files}")

    # Try filesystem_operations
    if hasattr(raw_result, "filesystem_operations"):
        print(f"\nfilesystem_operations: {raw_result.filesystem_operations}")


if __name__ == "__main__":
    asyncio.run(test_vfs())
