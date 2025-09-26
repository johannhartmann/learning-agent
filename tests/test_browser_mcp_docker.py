import os
import time

import pytest
import requests


pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _skip_if_no_llm_keys() -> None:
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        pytest.skip("No LLM API key configured; skipping browser MCP integration test")


def test_mcp_browser_end_to_end_via_server() -> None:
    """
    End-to-end test exercising browser-use via MCP inside the server container.

    Flow:
    - Create a thread on the LangGraph server
    - Ask the agent to visit the internal test page and extract the title using browser tools
    - Poll for run completion and verify output contains the page title

    Note: This test requires Docker services 'server' and 'postgres' to be up and an LLM key set.
    """
    _skip_if_no_llm_keys()

    base = os.getenv("SERVER_BASE", "http://server:2024")

    # 1) Create a thread
    r = requests.post(f"{base}/threads", json={}, timeout=30)
    r.raise_for_status()
    thread_id = r.json()["thread_id"]

    # 2) Instruct the agent to use browser tools deterministically
    prompt = (
        "Delegate browsing to the research subagent and use its tools.\n"
        "Steps:\n"
        "1) Call task(subagent_type=\"research-agent\") to open a browsing context.\n"
        "2) Use research_goto to open 'http://localhost:8001/api/testpage' (internal test page).\n"
        "3) Use research_extract_structured_data with the query 'page title' to read the exact page title text (one call is enough).\n"
        "4) Conclude with a brief synthesis and a bulleted Sources section as your final assistant message (do not call any completion tool)."
    )
    run_req = {
        "assistant_id": "learning_agent",
        "input": {
            "messages": [
                {"role": "user", "content": prompt},
            ]
        },
    }
    rr = requests.post(f"{base}/threads/{thread_id}/runs", json=run_req, timeout=30)
    rr.raise_for_status()
    run_id = rr.json()["run_id"]

    # 3) Poll for completion
    deadline = time.time() + 180  # up to 3 minutes to allow for cold start of browsers
    final_state = None
    while time.time() < deadline:
        time.sleep(3)
        sr = requests.get(f"{base}/threads/{thread_id}/runs/{run_id}", timeout=30)
        sr.raise_for_status()
        data = sr.json()
        if data.get("status") in {"success", "failed", "interrupted"}:
            # Fetch final state
            st = requests.get(f"{base}/threads/{thread_id}/state", timeout=30)
            st.raise_for_status()
            final_state = st.json()
            break

    assert final_state is not None, "Run did not complete in time"

    # 4) Validate that the assistant messages contain the expected title
    messages = (final_state or {}).get("values", {}).get("messages", [])
    text_blobs: list[str] = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            text_blobs.append(content)
        elif isinstance(content, list):
            text_blobs.extend(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )

    blob = "\n".join(text_blobs)
    assert "MCP Browser Test Page" in blob, f"Expected title not found in messages: {blob[:500]}"
