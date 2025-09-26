#!/usr/bin/env python
"""Test sandbox file tracking with matplotlib."""

import asyncio
import json

import httpx


async def test_matplotlib():
    """Test matplotlib plot generation and file tracking."""

    # Test code that generates a matplotlib plot
    test_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create a simple plot
x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('Test Sine Wave')
plt.xlabel('X')
plt.ylabel('Sin(X)')
plt.grid(True)

# Save the plot
plt.savefig('/tmp/test_plot.png')
print("Saved plot to /tmp/test_plot.png")

# Try saving as different formats
plt.savefig('/tmp/test_plot.svg')
print("Saved plot to /tmp/test_plot.svg")

# Create another plot
plt.figure()
plt.hist(np.random.randn(1000), bins=30)
plt.title('Histogram')
plt.savefig('/tmp/histogram.png')
print("Saved histogram to /tmp/histogram.png")
"""

    # Create a new thread
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create thread
        create_response = await client.post(
            "http://localhost:2024/threads",
            json={"metadata": {"test": "matplotlib"}},
            headers={"Content-Type": "application/json"},
        )
        thread = create_response.json()
        thread_id = thread["thread_id"]
        print(f"Created thread: {thread_id}")

        # Run the test
        run_response = await client.post(
            "http://localhost:2024/runs/stream",
            json={
                "thread_id": thread_id,
                "assistant_id": "learning_agent",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Please run this Python code:\n```python\n{test_code}\n```",
                        }
                    ]
                },
            },
            headers={"Content-Type": "application/json"},
        )

        # Collect the streamed response
        full_response = []
        async for line in run_response.aiter_lines():
            if line.startswith("data: "):
                try:
                    event_data = json.loads(line[6:])
                    full_response.append(event_data)
                    if event_data.get("event") == "metadata":
                        metadata = event_data.get("data", {})
                        if "run_id" in metadata:
                            print(f"Run ID: {metadata['run_id']}")
                except json.JSONDecodeError:
                    pass

        # Get the final state
        state_response = await client.get(
            f"http://localhost:2024/threads/{thread_id}/state",
            headers={"Content-Type": "application/json"},
        )

        state = state_response.json()
        files = state.get("values", {}).get("files", {})

        print("\n=== Files in state: ===")
        for filepath, content in files.items():
            # Content is base64 encoded
            print(f"  - {filepath}: {len(content)} bytes (base64)")

        # Check if images are accessible via API
        print("\n=== Testing file API access: ===")
        for filepath in files.keys():
            if filepath.endswith((".png", ".svg")):
                api_url = f"http://localhost:8001/api/files{filepath}?thread_id={thread_id}"
                file_response = await client.get(api_url)
                print(
                    f"  - {filepath}: status={file_response.status_code}, size={len(file_response.content)} bytes"
                )

        return files


if __name__ == "__main__":
    files = asyncio.run(test_matplotlib())
    print(f"\n✅ Test completed. Found {len(files)} files")
