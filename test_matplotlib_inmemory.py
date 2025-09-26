#!/usr/bin/env python3
"""Test matplotlib visualization with in-memory file serving."""

import asyncio
import json

import httpx


async def test_matplotlib_plot() -> None:
    """Test matplotlib plot generation with the new in-memory file system."""
    # Create a thread for the session
    import uuid

    thread_id = str(uuid.uuid4())

    # The matplotlib code to test
    matplotlib_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create a simple plot
x = np.linspace(0, 2 * np.pi, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', label='sin(x)')
plt.plot(x, np.cos(x), 'r--', label='cos(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Sine and Cosine Functions')
plt.legend()
plt.grid(True)
plt.savefig('/tmp/sine_cosine.png')
print("Plot saved to /tmp/sine_cosine.png")
print("Plot created successfully!")
"""

    # Prepare the message
    messages = [
        {
            "type": "human",
            "content": f"Please run this matplotlib code:\n\n```python\n{matplotlib_code}\n```",
        }
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Send the request to LangGraph server
        print(f"Sending matplotlib test to thread: {thread_id}")
        response = await client.post(
            f"http://localhost:2024/threads/{thread_id}/runs/stream",
            json={
                "assistant_id": "learning_agent",
                "input": {"messages": messages},
                "config": {"configurable": {"thread_id": thread_id}},
            },
            headers={"Content-Type": "application/json"},
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        # Process the stream
        print("\nStreaming response:")
        print("-" * 50)

        for line in response.iter_lines():
            if line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                if data:
                    try:
                        event = json.loads(data)
                        # Print relevant events
                        if event.get("type") == "messages":
                            for msg in event.get("data", []):
                                if msg.get("type") == "tool":
                                    print("\nTool response received")
                                elif msg.get("type") == "ai":
                                    content = msg.get("content", "")
                                    if content:
                                        print(f"\nAI: {content}")
                    except json.JSONDecodeError:
                        pass

        print("\n" + "-" * 50)

        # Now check the thread state to see if files are stored
        print("\nChecking thread state for stored files...")
        state_response = await client.get(
            f"http://localhost:2024/threads/{thread_id}/state",
            headers={"Content-Type": "application/json"},
        )

        if state_response.status_code == 200:
            state = state_response.json()
            session_files = state.get("values", {}).get("session_files", {})

            if session_files:
                print(f"✅ Found {len(session_files)} file(s) in session memory:")
                for filepath in session_files:
                    print(f"  - {filepath}")

                # Test fetching a file from the API server
                for filepath in session_files:
                    if filepath.endswith(".png"):
                        print(f"\nTesting file retrieval: {filepath}")
                        file_response = await client.get(
                            f"http://localhost:8001/api/files{filepath}?thread_id={thread_id}"
                        )

                        if file_response.status_code == 200:
                            print(
                                f"  ✅ Successfully retrieved file (size: {len(file_response.content)} bytes)"
                            )
                            print(f"  Content-Type: {file_response.headers.get('Content-Type')}")
                        else:
                            print(f"  ❌ Failed to retrieve file: {file_response.status_code}")
                            print(f"  Error: {file_response.text}")
                        break
            else:
                print("❌ No files found in session memory")
        else:
            print(f"Failed to get thread state: {state_response.status_code}")


if __name__ == "__main__":
    asyncio.run(test_matplotlib_plot())
