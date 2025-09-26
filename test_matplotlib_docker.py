#!/usr/bin/env python
"""Test matplotlib generation through the Docker server."""

import time

import requests


def test_matplotlib():
    print("Testing matplotlib plot generation...")

    # Create a thread first
    thread_resp = requests.post(
        "http://localhost:2024/threads", json={}, headers={"Content-Type": "application/json"}
    )

    if thread_resp.status_code != 200:
        print(f"Failed to create thread: {thread_resp.status_code}")
        print(thread_resp.text)
        return

    thread_id = thread_resp.json()["thread_id"]
    print(f"Created thread: {thread_id}")

    # Send matplotlib request
    response = requests.post(
        f"http://localhost:2024/threads/{thread_id}/runs",
        json={
            "assistant_id": "learning_agent",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": "Create a simple matplotlib plot showing y=x^2 from -5 to 5. Save the plot as plot.png.",
                    }
                ]
            },
        },
        headers={"Content-Type": "application/json"},
    )

    if response.status_code != 200:
        print(f"Failed to start run: {response.status_code}")
        print(response.text)
        return

    run_id = response.json()["run_id"]
    print(f"Started run: {run_id}")

    # Poll for completion
    for _ in range(30):
        time.sleep(2)
        status_resp = requests.get(f"http://localhost:2024/threads/{thread_id}/runs/{run_id}")

        if status_resp.status_code != 200:
            print(f"Failed to get run status: {status_resp.status_code}")
            continue

        status = status_resp.json()["status"]
        print(f"Run status: {status}")

        if status in ["success", "error"]:
            # Get the final state
            state_resp = requests.get(f"http://localhost:2024/threads/{thread_id}/state")

            if state_resp.status_code == 200:
                state = state_resp.json()

                # Check for files in state
                if "values" in state and "files" in state["values"]:
                    files = state["values"]["files"]
                    print(f"\nFiles in state: {list(files.keys()) if files else 'None'}")

                    for fname, content in files.items():
                        if fname.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                            print(f"✓ Image file found: {fname} ({len(content)} bytes)")
                else:
                    print("\nNo files field in state")

                # Check messages
                if "values" in state and "messages" in state["values"]:
                    messages = state["values"]["messages"]
                    for msg in messages[-3:]:  # Last 3 messages
                        if "content" in msg:
                            content = msg["content"]
                            if "plot" in content.lower() or ".png" in content:
                                print(f"\nPlot reference in message: {content[:200]}")
            break

    print("\nTest complete!")


if __name__ == "__main__":
    test_matplotlib()
