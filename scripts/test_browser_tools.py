"""Quick smoke test for MCP browser tools.

The script creates the learning agent and asks it to retrieve the latest
headlines from https://www.heise.de/. It prints the assistant's final reply
so you can verify the research tools are functioning end-to-end.

Ensure the MCP browser dependencies (Playwright, etc.) are installed; the
browser tools are always enabled in the agent.
"""

from __future__ import annotations

import asyncio
from typing import Any

from learning_agent.agent import create_learning_agent
from learning_agent.tools.mcp_browser import shutdown_mcp_browser


async def run_browser_smoke_test() -> None:
    agent = create_learning_agent()

    prompt = (
        "Use the research-agent to open https://www.heise.de/ and summarize "
        "the current top stories. Provide a short bulleted list with titles "
        "and canonical URLs."
    )

    state: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        result = await agent.ainvoke(state)
    finally:
        await shutdown_mcp_browser()

    messages = result.get("messages", [])
    if not messages:
        print("No messages returned from agent.")
        return

    last_message = messages[-1]
    content = getattr(last_message, "content", last_message)

    print("\n=== Agent Response ===\n")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                print(block.get("text", ""))
    else:
        print(content)

    files = result.get("files", {})
    if files:
        print("\n=== Files returned ===")
        for path in files:
            print(f"- {path}")


if __name__ == "__main__":
    asyncio.run(run_browser_smoke_test())
