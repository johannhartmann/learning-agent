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
_started: bool = False


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


async def _ensure_browser() -> Browser:
    global _browser
    global _started
    if _browser is not None and _started:
        return _browser

    allowed = _parse_allowed_domains()
    headless = _truthy("BROWSER_HEADLESS", True)
    keep_alive = _truthy("BROWSER_KEEP_ALIVE", True)

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

    if _browser is None:
        _browser = Browser(**kwargs)
    if not _started:
        # Ensure session is live so multiple Agent runs share state
        await _browser.start()  # type: ignore[attr-defined]
        _started = True
    return _browser


def _get_llm():
    # Use configured provider/model; fall back to OpenAI
    model = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    return ChatOpenAI(model=model)


@mcp.tool()
async def go_to_url(url: str) -> str:
    """Navigate to a URL and wait for page to load."""
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Go to {url} and wait until the page is loaded. Then say 'ready'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "navigated"


@mcp.tool()
async def extract_structured_data(query: str) -> str:
    """Use browser-use's extraction to get structured data based on a query."""
    browser = await _ensure_browser()
    llm = _get_llm()
    task = (
        "On the current page, use extract_structured_data to return exactly what is asked: "
        f"{query}"
    )
    agent = Agent(task=task, browser_session=browser, llm=llm)
    result = await agent.run(max_steps=4)
    return str(result)


# ---- Additional default tools exposed ----


@mcp.tool()
async def search_google(query: str) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = (
        f"Use search_google to find results for: {query}. Return the top 3 result titles and URLs."
    )
    agent = Agent(task=task, browser_session=browser, llm=llm)
    result = await agent.run(max_steps=4)
    return str(result)


@mcp.tool()
async def wait(seconds: float = 2.0) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Wait for {seconds} seconds, then say 'done waiting'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "waited"


@mcp.tool()
async def scroll(pixels: int = 800) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Scroll the page vertically by {pixels} pixels, then say 'scrolled'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "scrolled"


@mcp.tool()
async def send_keys(keys: str) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Use send_keys with the sequence: {keys}. Then say 'keys sent'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "keys_sent"


@mcp.tool()
async def switch_tab(index: int = 0) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Switch to tab at index {index}. Then say 'tab switched'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "tab_switched"


@mcp.tool()
async def close_tab(index: int | None = None) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    which = "the current tab" if index is None else f"tab at index {index}"
    task = f"Close {which}. Then say 'tab closed'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "tab_closed"


@mcp.tool()
async def input_text(selector: str, text: str) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = (
        f"Find element '{selector}' and input the following text: {text!r}. Then say 'input done'."
    )
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=3)
    return "input_done"


@mcp.tool()
async def click_element_by_index(index: int) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Use click_element_by_index on index {index}. Then say 'clicked'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=2)
    return "clicked"


@mcp.tool()
async def scroll_to_text(text: str) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Use scroll_to_text to bring '{text}' into view. Then say 'ready'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=3)
    return "ready"


@mcp.tool()
async def get_dropdown_options(selector: str) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Get dropdown options for element '{selector}' and return them as a list."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    result = await agent.run(max_steps=3)
    return str(result)


@mcp.tool()
async def select_dropdown_option(selector: str, value: str) -> str:
    browser = await _ensure_browser()
    llm = _get_llm()
    task = f"Select option '{value}' for dropdown '{selector}'. Then say 'selected'."
    agent = Agent(task=task, browser_session=browser, llm=llm)
    await agent.run(max_steps=3)
    return "selected"


if __name__ == "__main__":
    mcp.run(transport="stdio")
