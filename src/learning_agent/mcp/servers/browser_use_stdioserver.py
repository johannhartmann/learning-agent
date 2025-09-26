"""MCP stdio server implementing atomic browser actions with Playwright.

Tools (mirror Playwright `Page` APIs):
- goto(url, wait_until?, timeout?, referer?)
- wait_for_timeout(timeout)
- keyboard_type(text, delay?)
- mouse_wheel(delta_x, delta_y)
- bring_to_front()
- close(run_before_unload?)
- screenshot(path?, full_page?, omit_background?, type?, quality?)
- extract_structured_data(query, extract_links?, start_from_char?)
- url()

Configuration via environment variables (see mcp_browser.py):
- BROWSER_HEADLESS: true/false
- BROWSER_VIEWPORT_WIDTH / BROWSER_VIEWPORT_HEIGHT: integers
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any
try:
    from playwright.async_api import async_playwright, Page
    HAVE_PW = True
except Exception:  # pragma: no cover - optional dependency path
    async_playwright = None  # type: ignore[assignment]
    Page = object  # type: ignore[assignment]
    HAVE_PW = False
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import logging


mcp = FastMCP("BrowserUse")
logger = logging.getLogger(__name__)

# Playwright globals
_pw = None
_pw_browser = None
_pw_context = None
_pw_page: Page | None = None  # type: ignore[assignment]

MAX_STRUCTURED_CHARS = 30_000


def _truthy(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def _viewport() -> dict[str, int] | None:
    try:
        vw = int(os.getenv("BROWSER_VIEWPORT_WIDTH", "0"))
        vh = int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "0"))
        if vw > 0 and vh > 0:
            return {"width": vw, "height": vh}
    except Exception:
        return None
    return None


async def _ensure_playwright() -> Page:
    """Ensure a shared Playwright page is available."""
    global _pw, _pw_browser, _pw_context, _pw_page
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    if _pw_page is not None:
        return _pw_page
    _pw = await async_playwright().start()
    headless = _truthy("BROWSER_HEADLESS", True)

    _pw_browser = await _pw.chromium.launch(headless=headless)
    vp = _viewport()
    ctx_kwargs: dict[str, Any] = {}
    if vp:
        ctx_kwargs["viewport"] = vp
    _pw_context = await _pw_browser.new_context(**ctx_kwargs)

    _pw_page = await _pw_context.new_page()
    return _pw_page


def _get_llm():
    # No LLM used in Playwright-only implementation. Kept for compatibility.
    return None


def _clean_page_content(html: str, extract_links: bool = False) -> tuple[str, dict[str, Any], list[dict[str, str]]]:
    """Convert raw HTML into a whitespace-normalised plaintext snippet."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "canvas"]):
        tag.decompose()

    links: list[dict[str, str]] = []
    if extract_links:
        for anchor in soup.find_all("a"):
            text = anchor.get_text(" ", strip=True)
            href = anchor.get("href") or ""
            if text or href:
                links.append({"text": text, "href": href})
        # Deduplicate while preserving order and limit volume
        seen: set[tuple[str, str]] = set()
        unique_links: list[dict[str, str]] = []
        for item in links:
            key = (item["text"], item["href"])
            if key in seen:
                continue
            seen.add(key)
            unique_links.append(item)
            if len(unique_links) >= 100:
                break
        links = unique_links

    text_raw = soup.get_text("\n")
    collapsed_lines: list[str] = []
    for line in text_raw.splitlines():
        normalised = re.sub(r"\s+", " ", line).strip()
        if normalised:
            collapsed_lines.append(normalised)
    cleaned_text = "\n".join(collapsed_lines)

    stats = {
        "original_html_chars": len(html),
        "initial_text_chars": len(text_raw),
        "filtered_text_chars": len(cleaned_text),
        "filtered_chars_removed": max(len(text_raw) - len(cleaned_text), 0),
    }

    return cleaned_text, stats, links


def _smart_truncate(text: str, limit: int = MAX_STRUCTURED_CHARS) -> int:
    if len(text) <= limit:
        return len(text)
    paragraph_break = text.rfind("\n\n", max(0, limit - 500), limit)
    if paragraph_break != -1:
        return paragraph_break
    sentence_break = text.rfind(". ", max(0, limit - 200), limit)
    if sentence_break != -1:
        return sentence_break + 1
    return limit


@mcp.tool()
async def goto(
    url: str,
    wait_until: str | None = None,
    timeout: float | None = None,
    referer: str | None = None,
) -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    kwargs: dict[str, Any] = {}
    if wait_until is not None:
        kwargs["wait_until"] = wait_until
    if timeout is not None:
        kwargs["timeout"] = timeout
    if referer is not None:
        kwargs["referer"] = referer
    await page.goto(url, **kwargs)
    return json.dumps({"action": "goto", "status": "ok", "url": page.url})


@mcp.tool()
async def wait_for_timeout(timeout: float) -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    await page.wait_for_timeout(timeout)
    return json.dumps({"action": "wait_for_timeout", "status": "ok", "timeout": timeout, "url": page.url})


@mcp.tool()
async def keyboard_type(text: str, delay: float | None = None) -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    kwargs: dict[str, Any] = {}
    if delay is not None:
        kwargs["delay"] = delay
    await page.keyboard.type(text, **kwargs)
    return json.dumps({"action": "keyboard_type", "status": "ok", "text": text, "url": page.url})


@mcp.tool()
async def mouse_wheel(delta_x: float = 0, delta_y: float = 0) -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    await page.mouse.wheel(delta_x, delta_y)
    return json.dumps({"action": "mouse_wheel", "status": "ok", "delta_x": delta_x, "delta_y": delta_y, "url": page.url})


@mcp.tool()
async def bring_to_front() -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    await page.bring_to_front()
    return json.dumps({"action": "bring_to_front", "status": "ok", "url": page.url})


@mcp.tool()
async def close(run_before_unload: bool | None = None) -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    kwargs: dict[str, Any] = {}
    if run_before_unload is not None:
        kwargs["run_before_unload"] = run_before_unload
    await page.close(**kwargs)
    # Reset cached page so the next tool call creates a fresh one
    global _pw_page
    _pw_page = None
    return json.dumps({"action": "close", "status": "ok"})


@mcp.tool()
async def screenshot(
    path: str | None = None,
    full_page: bool | None = None,
    omit_background: bool | None = None,
    type: str | None = None,
    quality: int | None = None,
) -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    kwargs: dict[str, Any] = {}
    if path is not None:
        kwargs["path"] = path
    if full_page is not None:
        kwargs["full_page"] = full_page
    if omit_background is not None:
        kwargs["omit_background"] = omit_background
    if type is not None:
        kwargs["type"] = type
    if quality is not None:
        kwargs["quality"] = quality
    image_bytes = await page.screenshot(**kwargs)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return json.dumps(
        {
            "action": "screenshot",
            "status": "ok",
            "url": page.url,
            "path": path,
            "image_base64": encoded,
        }
    )


@mcp.tool()
async def url() -> str:
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    page = await _ensure_playwright()
    return json.dumps({"action": "url", "status": "ok", "url": page.url})


@mcp.tool()
async def extract_structured_data(
    query: str,
    extract_links: bool = False,
    start_from_char: int = 0,
) -> str:
    """Return filtered page content suitable for downstream structured extraction."""
    if not HAVE_PW:
        raise RuntimeError("playwright not available")
    if start_from_char < 0:
        raise ValueError("start_from_char must be >= 0")

    page = await _ensure_playwright()
    html = await page.content()
    cleaned_text, stats, links = _clean_page_content(html, extract_links=extract_links)

    total_chars = len(cleaned_text)
    if start_from_char >= total_chars:
        return json.dumps(
            {
                "action": "extract_structured_data",
                "status": "error",
                "reason": "start_from_char_out_of_range",
                "start_from_char": start_from_char,
                "total_chars": total_chars,
                "url": page.url,
            }
        )

    segment_source = cleaned_text[start_from_char:]
    truncate_at = _smart_truncate(segment_source, MAX_STRUCTURED_CHARS)
    segment = segment_source[:truncate_at]
    truncated = start_from_char + truncate_at < total_chars
    next_start = start_from_char + truncate_at if truncated else None

    payload: dict[str, Any] = {
        "action": "extract_structured_data",
        "status": "ok",
        "query": query,
        "url": page.url,
        "content": segment,
        "start_from_char": start_from_char,
        "truncated": truncated,
        "total_filtered_chars": total_chars,
        "stats": stats,
    }
    if next_start is not None:
        payload["next_start_char"] = next_start
    if extract_links and links:
        payload["links"] = links

    return json.dumps(payload)


if __name__ == "__main__":
    mcp.run(transport="stdio")
