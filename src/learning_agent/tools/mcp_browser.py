"""MCP adapter for a Playwright-based browser stdio server, exposed as LangChain tools.

This module spawns our MCP server via stdio and wraps its tools for use inside the agent.
It is safe to import when adapters are missing (returns []).

Environment variables (see .env.example) map to server parameters:
- BROWSER_HEADLESS: boolean
- BROWSER_VIEWPORT_WIDTH, BROWSER_VIEWPORT_HEIGHT: ints
"""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import logging
from typing import Any

from anyio import ClosedResourceError

try:  # Optional during import-time when not running agents
    from langchain_core.tools import tool as lc_tool, StructuredTool  # type: ignore[import-not-found]
    from langchain_mcp_adapters.client import create_session, MultiServerMCPClient  # type: ignore[import-not-found]
    from langchain_mcp_adapters.tools import (  # type: ignore[import-not-found]
        _convert_call_tool_result,
        load_mcp_tools,
    )
except Exception:  # pragma: no cover - fallback when adapters not installed
    lc_tool = None  # type: ignore[assignment]
    StructuredTool = Any  # type: ignore[assignment]
    create_session = None  # type: ignore[assignment]
    load_mcp_tools = None  # type: ignore[assignment]
    _convert_call_tool_result = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _truthy(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


"""Singleton MCP client + tool wrappers

This module returns the MCP browser tools and ensures they are backed by a
single long-lived MCP client process so that Playwright state persists across
multiple tool invocations. Without this, each tool call may spin up a fresh
stdio server that starts on about:blank, breaking flows that expect, for
example, `research_goto` followed by DOM interactions.
"""

# Global singletons to keep the MCP stdio server alive across tool calls
_MCP_TOOLS_CACHE: list[Any] | None = None
_MCP_SESSION_CTX: Any | None = None
_MCP_SESSION: Any | None = None
_MCP_SESSION_LOCK: asyncio.Lock | None = None
_MCP_SESSION_LOOP: asyncio.AbstractEventLoop | None = None
_SERVER_CFG: dict[str, Any] | None = None


async def _create_session_locked() -> None:
    global _MCP_SESSION_CTX, _MCP_SESSION, _MCP_SESSION_LOOP
    if _SERVER_CFG is None:
        raise RuntimeError("MCP server not configured")
    session_cm = create_session(_SERVER_CFG)
    session = await session_cm.__aenter__()
    await session.initialize()
    _MCP_SESSION_CTX = session_cm
    _MCP_SESSION = session
    _MCP_SESSION_LOOP = asyncio.get_running_loop()


async def _close_session_locked() -> None:
    global _MCP_SESSION_CTX, _MCP_SESSION, _MCP_SESSION_LOOP
    session_cm = _MCP_SESSION_CTX
    if session_cm is None:
        return
    try:
        await session_cm.__aexit__(None, None, None)
    except RuntimeError as err:
        if "Attempted to exit cancel scope" in str(err):
            logger.debug("MCP session already closing; ignoring cancel scope warning")
        else:
            logger.exception("Error closing MCP session context")
    except Exception:
        logger.exception("Error closing MCP session context")
    finally:
        _MCP_SESSION_CTX = None
        _MCP_SESSION = None
        _MCP_SESSION_LOOP = None


async def _ensure_session() -> Any:
    global _MCP_SESSION_LOCK
    if _MCP_SESSION is not None:
        return _MCP_SESSION
    if _MCP_SESSION_LOCK is None:
        _MCP_SESSION_LOCK = asyncio.Lock()
    async with _MCP_SESSION_LOCK:
        if _MCP_SESSION is None:
            await _create_session_locked()
    return _MCP_SESSION


async def _reset_session() -> None:
    global _MCP_SESSION_LOCK, _MCP_SESSION_CTX, _MCP_SESSION
    if _MCP_SESSION_LOCK is None:
        _MCP_SESSION_LOCK = asyncio.Lock()
    async with _MCP_SESSION_LOCK:
        await _close_session_locked()
        await _create_session_locked()


async def _call_tool_with_session(name: str, arguments: dict[str, Any]) -> tuple[str | list[str], list[Any] | None]:
    if _convert_call_tool_result is None:
        raise RuntimeError("langchain-mcp-adapters conversion unavailable")
    session = await _ensure_session()
    try:
        result = await session.call_tool(name, arguments)
    except ClosedResourceError:
        await _reset_session()
        session = await _ensure_session()
        result = await session.call_tool(name, arguments)
    return _convert_call_tool_result(result)



async def _shutdown_session_async() -> None:
    global _MCP_SESSION_LOCK
    if _MCP_SESSION_LOCK is None:
        _MCP_SESSION_LOCK = asyncio.Lock()
    async with _MCP_SESSION_LOCK:
        await _close_session_locked()


async def shutdown_mcp_browser() -> None:
    """Close the shared MCP session if it is active."""
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    if _MCP_SESSION_LOOP is not None and loop is not None and _MCP_SESSION_LOOP is not loop:
        future = asyncio.run_coroutine_threadsafe(_shutdown_session_async(), _MCP_SESSION_LOOP)
        await asyncio.wrap_future(future)
        return

    await _shutdown_session_async()


def shutdown_mcp_browser_sync(timeout: float | None = None) -> None:
    """Synchronous helper to close the MCP session from non-async contexts."""
    loop = _MCP_SESSION_LOOP
    if loop is None:
        return
    try:
        future = asyncio.run_coroutine_threadsafe(_shutdown_session_async(), loop)
        future.result(timeout)
    except RuntimeError:
        # Event loop already closed; nothing we can do.
        return
    except Exception:
        logger.exception("Synchronous MCP shutdown failed")


atexit.register(shutdown_mcp_browser_sync)


def create_mcp_browser_tools() -> list[Any]:  # returns LangChain tools when available
    if (
        load_mcp_tools is None
        or create_session is None
        or StructuredTool is Any
        or _convert_call_tool_result is None
    ):
        logger.warning("MCP adapters not available; browser tools disabled")
        return []

    global _SERVER_CFG, _MCP_TOOLS_CACHE

    if _MCP_TOOLS_CACHE is not None:
        try:
            names = [getattr(t, "name", "<unnamed>") for t in _MCP_TOOLS_CACHE]
        except Exception:
            names = ["<error>"]
        logger.info(
            "Reusing cached MCP browser tools (count=%d): %s",
            len(_MCP_TOOLS_CACHE),
            names,
        )
        return _MCP_TOOLS_CACHE

    inherit_keys = (
        "DISPLAY",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "XDG_RUNTIME_DIR",
    )
    server_env: dict[str, str] = {
        key: value for key in inherit_keys if (value := os.getenv(key))
    }

    server_env["BROWSER_HEADLESS"] = "true" if _truthy("BROWSER_HEADLESS", True) else "false"
    server_env["BROWSER_KEEP_ALIVE"] = "true" if _truthy("BROWSER_KEEP_ALIVE", False) else "false"

    if val := os.getenv("BROWSER_MIN_WAIT"):
        server_env["BROWSER_MIN_WAIT"] = val
    if val := os.getenv("BROWSER_WAIT_BETWEEN"):
        server_env["BROWSER_WAIT_BETWEEN"] = val
    vw = os.getenv("BROWSER_VIEWPORT_WIDTH")
    vh = os.getenv("BROWSER_VIEWPORT_HEIGHT")
    if vw and vh:
        server_env["BROWSER_VIEWPORT"] = json.dumps({"width": int(vw), "height": int(vh)})

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

    command = os.getenv("BROWSER_MCP_COMMAND", "python")
    args_env = os.getenv("BROWSER_MCP_ARGS")
    if args_env:
        args = args_env.split()
    else:
        args = ["-m", "learning_agent.mcp.servers.browser_use_stdioserver"]

    server_cfg: dict[str, Any] = {"command": command, "args": args, "transport": "stdio"}
    if server_env:
        existing_env = server_cfg.get("env", {})
        merged_env = {**existing_env, **server_env}
        server_cfg["env"] = merged_env
    _SERVER_CFG = server_cfg

    async def _load() -> list[Any]:
        client = MultiServerMCPClient({"browser": server_cfg})
        return await client.get_tools()

    from threading import Thread

    result: list[list[Any]] = []
    exc: list[BaseException] = []

    def _runner() -> None:
        try:
            import anyio

            res = anyio.run(_load)
            result.append(res)
        except BaseException as e:
            exc.append(e)

    thread = Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if exc:
        logger.exception("Failed to load MCP browser tools: %s", exc[0])
        return []
    if not result:
        logger.warning("MCP browser tools load returned no result tuple")
        return []

    tools_raw = result[0]

    if lc_tool is not None:

        @lc_tool("research_done")  # type: ignore[misc]
        def _research_done_tool(reason: str | None = None) -> str:
            """Mark research as complete with an optional reason."""
            msg = "Research complete"
            if reason:
                msg += f": {reason}"
            return msg

    else:  # pragma: no cover - fallback if adapters not present
        _research_done_tool = None  # type: ignore[assignment]

    tools_prepared: list[Any] = []

    for tool_obj in tools_raw:
        base_name = getattr(tool_obj, "name", "")
        args_schema = getattr(tool_obj, "args_schema", None)
        description = getattr(tool_obj, "description", "")
        metadata = getattr(tool_obj, "metadata", None)

        async def _wrapped_tool(*, __original_name: str = base_name, **kwargs: Any) -> tuple[str | list[str], list[Any] | None]:
            return await _call_tool_with_session(__original_name, kwargs)

        structured = StructuredTool(
            name=f"research_{base_name}",
            description=description,
            args_schema=args_schema,
            coroutine=_wrapped_tool,
            metadata=metadata,
            response_format="content_and_artifact",
        )
        tools_prepared.append(structured)

    if _research_done_tool is not None and not any(
        getattr(t, "name", "") == "research_done" for t in tools_prepared
    ):
        tools_prepared.append(_research_done_tool)

    _MCP_TOOLS_CACHE = tools_prepared

    try:
        names = [getattr(t, "name", "<unnamed>") for t in tools_prepared]
    except Exception:
        names = ["<error>"]

    logger.info(
        "Initialized MCP browser stdio client; tools available (count=%d): %s",
        len(tools_prepared),
        names,
    )

    return tools_prepared
