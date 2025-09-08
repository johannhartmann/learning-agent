"""Simple MCP stdio server wrapping browser-use Agent actions.

Exposes minimal tools used by integration tests:
- go_to_url(url: str)
- extract_structured_data(query: str)

Configuration is via environment variables documented in mcp_browser.py.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Import browser-use primitives
from browser_use import Agent, Browser, ChatOpenAI
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("BrowserUse")

# Singleton browser instance (kept alive across calls)
_browser: Browser | None = None


def _truthy(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def _parse_allowed_domains() -> list[str] | None:
    raw = os.getenv("BROWSER_ALLOWED_DOMAINS")
    if not raw:
        return None
    try:
        if raw.strip().startswith("["):
            arr = json.loads(raw)
            return [str(x) for x in arr]
    except Exception:
        pass
    return [p.strip() for p in raw.split(",") if p.strip()]


def _get_browser() -> Browser:
    global _browser
    if _browser is not None:
        return _browser

    allowed = _parse_allowed_domains()
    headless = _truthy("BROWSER_HEADLESS", True)
    keep_alive = _truthy("BROWSER_KEEP_ALIVE", False)

    viewport = None
    try:
        vw = int(os.getenv("BROWSER_VIEWPORT_WIDTH", "0"))
        vh = int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "0"))
        if vw > 0 and vh > 0:
            viewport = {"width": vw, "height": vh}
    except Exception:
        viewport = None

    kwargs: dict[str, Any] = {
        "headless": headless,
        "keep_alive": keep_alive,
    }
    if allowed:
        kwargs["allowed_domains"] = allowed
    if viewport:
        kwargs["viewport"] = viewport

    cdp = os.getenv("BROWSER_CDP_URL")
    if cdp:
        kwargs["cdp_url"] = cdp

    _browser = Browser(**kwargs)
    return _browser


def _get_llm():
    # Use configured provider/model; fall back to OpenAI
    model = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    return ChatOpenAI(model=model)


@mcp.tool()
async def go_to_url(url: str) -> str:
    """Navigate to a URL and wait for page to load."""
    browser = _get_browser()
    llm = _get_llm()
    task = f"Go to {url} and wait until the page is loaded. Then say 'ready'."
    agent = Agent(task=task, browser=browser, llm=llm)
    await agent.run(max_steps=2)
    return "navigated"


@mcp.tool()
async def extract_structured_data(query: str) -> str:
    """Use browser-use's extraction to get structured data based on a query."""
    browser = _get_browser()
    llm = _get_llm()
    task = (
        "On the current page, use extract_structured_data to return exactly what is asked: "
        f"{query}"
    )
    agent = Agent(task=task, browser=browser, llm=llm)
    result = await agent.run(max_steps=4)
    return str(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
