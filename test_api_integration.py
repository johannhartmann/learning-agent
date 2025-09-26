#!/usr/bin/env python3
"""Test API integration for serving matplotlib plots."""

import asyncio
import base64

import requests

from learning_agent.api_server import file_store
from learning_agent.tools.sandbox_tool import get_sandbox


async def test_api_integration() -> None:
    """Test that files are stored and served by the API."""

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
    print("STEP 1: SANDBOX EXECUTION")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Files: {result.get('files', [])}")

    # Manually store the file data in the file_store (simulating what python_sandbox would do)
    files_data = result.get("files_data", {})
    for file_path, data_b64 in files_data.items():
        file_bytes = base64.b64decode(data_b64)
        file_store[file_path] = file_bytes
        print(f"Stored {len(file_bytes)} bytes for {file_path}")

    print("\n" + "=" * 60)
    print("STEP 2: API FILE RETRIEVAL")
    print("=" * 60)

    # Test API retrieval for each file
    for file_path in result.get("files", []):
        # Try different URL patterns
        test_urls = [
            f"http://localhost:8001/api/files{file_path}",
            f"http://localhost:8001/api/files/{file_path.lstrip('/')}",
        ]

        for url in test_urls:
            print(f"\nTrying: {url}")
            try:
                response = requests.get(url, timeout=5)
                print(f"Status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

                if response.status_code == 200:
                    print(f"Content size: {len(response.content)} bytes")
                    # Check if it's a valid PNG
                    if response.content[:8] == b"\x89PNG\r\n\x1a\n":
                        print("✅ Valid PNG image received!")
                    elif b"<svg" in response.content[:100]:
                        print("⚠️ SVG placeholder received (not actual image)")
                    else:
                        print(f"Unknown content type, first bytes: {response.content[:20]}")
                    break
                print(f"Error: {response.text}")
            except Exception as e:
                print(f"Request failed: {e}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files in store: {list(file_store.keys())}")
    print(f"Total files stored: {len(file_store)}")


if __name__ == "__main__":
    asyncio.run(test_api_integration())
