#!/usr/bin/env python
"""Test sandbox filesystem directly."""

import asyncio

from langchain_sandbox.pyodide import PyodideSandbox


async def test_files():
    """Test file creation and retrieval."""

    sandbox = PyodideSandbox(
        stateful=False,
        allow_net=False,
        allow_read=["/app/node_modules"],
        allow_write=["/app/node_modules", "/tmp"],
    )

    # Test code that creates an image file
    test_code = """
import base64

# Create a simple PNG image (1x1 red pixel)
png_data = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIA30'
    'ztcAAAAABJRU5ErkJggg=='
)

# Save to file
with open('/tmp/test.png', 'wb') as f:
    f.write(png_data)

print("Created /tmp/test.png")

# Read it back
with open('/tmp/test.png', 'rb') as f:
    data = f.read()
    print(f"File size: {len(data)} bytes")
"""

    result = await sandbox.execute(test_code)

    print(f"Status: {result.status}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")
    print(f"Files: {result.files}")
    print(f"Filesystem ops: {result.filesystem_operations}")
    print(f"Filesystem info: {result.filesystem_info}")


if __name__ == "__main__":
    asyncio.run(test_files())
