"""MCP adapter for browser-use, exposed as LangChain tools.

This module spawns a browser-use MCP server via stdio and wraps its tools
for use inside our agent. It is gated by `ENABLE_MCP_BROWSER` and is safe to
import when dependencies are missing (returns []).

Environment variables (see .env.example) map to browser-use parameters:
- ENABLE_MCP_BROWSER: enable/disable tool exposure
- BROWSER_CDP_URL: optional existing browser CDP URL
- BROWSER_ALLOWED_DOMAINS: comma-separated allowlist (e.g., "*.example.com,docs.python.org")
- BROWSER_HEADLESS, BROWSER_KEEP_ALIVE: booleans
- BROWSER_MIN_WAIT, BROWSER_WAIT_BETWEEN: floats
- BROWSER_VIEWPORT_WIDTH, BROWSER_VIEWPORT_HEIGHT: ints
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any


def _truthy(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def _maybe(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value or None


def _parse_allowed_domains(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def create_mcp_browser_tools() -> list[Any]:  # returns LangChain tools when available
    try:
        # Use adapters client that creates a fresh session per tool invocation
        from langchain_mcp_adapters.client import (
            MultiServerMCPClient,  # type: ignore[import-not-found]
        )
    except Exception as e:  # pragma: no cover - optional dependency path
        print(f"MCP browser tools unavailable (missing adapters): {e}")
        return []

    # Build environment for the MCP server so it can configure the Browser()
    server_env: dict[str, str] = {}

    # Map key browser-use parameters via environment for the MCP server
    allowed = _parse_allowed_domains(os.getenv("BROWSER_ALLOWED_DOMAINS"))
    if allowed:
        server_env["BROWSER_ALLOWED_DOMAINS"] = json.dumps(allowed)

    # Booleans
    server_env["BROWSER_HEADLESS"] = "true" if _truthy("BROWSER_HEADLESS", True) else "false"
    server_env["BROWSER_KEEP_ALIVE"] = "true" if _truthy("BROWSER_KEEP_ALIVE", False) else "false"

    # Numbers
    if val := os.getenv("BROWSER_MIN_WAIT"):
        server_env["BROWSER_MIN_WAIT"] = val
    if val := os.getenv("BROWSER_WAIT_BETWEEN"):
        server_env["BROWSER_WAIT_BETWEEN"] = val
    # Viewport
    vw = os.getenv("BROWSER_VIEWPORT_WIDTH")
    vh = os.getenv("BROWSER_VIEWPORT_HEIGHT")
    if vw and vh:
        server_env["BROWSER_VIEWPORT"] = json.dumps({"width": int(vw), "height": int(vh)})

    # CDP URL (connect to existing browser) or empty to let server launch Chromium
    cdp = _maybe(os.getenv("BROWSER_CDP_URL"))
    if cdp:
        server_env["BROWSER_CDP_URL"] = cdp

    # Propagate LLM credentials/env if present
    for key in [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "TOGETHER_API_KEY",
        "FIREWORKS_API_KEY",
    ]:
        val = os.getenv(key)
        if val:
            server_env[key] = val

    # Command to launch browser-use MCP server; allow override
    command = os.getenv("BROWSER_MCP_COMMAND", "python")
    args_env = os.getenv("BROWSER_MCP_ARGS")
    if args_env:
        args = args_env.split()
    else:
        # Use our bundled stdio MCP server that wraps browser-use
        args = ["-m", "learning_agent.mcp.servers.browser_use_stdioserver"]

    try:
        # Build client config for stdio server
        server_cfg: dict[str, Any] = {"command": command, "args": args, "transport": "stdio"}
        if server_env:
            server_cfg["env"] = server_env

        async def _load() -> list[Any]:
            client = MultiServerMCPClient({"browser": server_cfg})
            tools = await client.get_tools()
            return list(tools)

        # Synchronously load tools at startup time.
        # Use a dedicated thread + event loop to avoid conflicts with any running loop.
        from threading import Thread

        result: list[list[Any]] = []
        exc: list[BaseException] = []

        def _runner() -> None:
            try:
                res = asyncio.run(_load())
                result.append(res)
            except BaseException as e:
                exc.append(e)

        t = Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        if exc:
            print(f"Failed to load MCP tools in thread: {exc[0]}")
            return []
        return result[0] if result else []
    except Exception as e:  # pragma: no cover - runtime issues
        print(f"Failed to initialize browser MCP tools: {e}")
        return []
