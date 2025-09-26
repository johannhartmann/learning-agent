"""Run the MCP browser tools via a LangChain ReAct agent to fetch heise.de headlines."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from learning_agent.config import settings
from learning_agent.providers import get_chat_model
from learning_agent.tools.mcp_browser import (
    create_mcp_browser_tools,
    shutdown_mcp_browser,
)

USER_PROMPT = (
    "Visit https://www.heise.de/, handle any consent prompts if needed, and return "
    "the latest top stories with their canonical URLs."
)


async def run() -> None:
    def _preview(value: Any, limit: int = 240) -> str:
        text = repr(value)
        return text if len(text) <= limit else text[:limit] + "…"

    def _extract_tool_name(event: Dict[str, Any]) -> Optional[str]:
        """Best-effort extraction of tool name across langgraph event payload variants."""

        def _maybe_from_dict(value: Any) -> Optional[str]:
            if isinstance(value, dict):
                inner_name = value.get("name")
                if isinstance(inner_name, str) and inner_name.strip():
                    return inner_name
            return None

        candidates: list[Any] = []
        # langgraph usually sets the tool name at the top level
        candidates.append(event.get("name"))

        metadata = event.get("metadata")
        if isinstance(metadata, dict):
            candidates.extend(
                metadata.get(key)
                for key in ("tool", "tool_name", "name")
            )

        data = event.get("data")
        if isinstance(data, dict):
            candidates.extend(
                data.get(key)
                for key in ("name", "tool", "tool_name")
            )
            serialized = data.get("serialized")
            if isinstance(serialized, dict):
                candidates.extend(serialized.get(key) for key in ("name", "tool"))

        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate
            extracted = _maybe_from_dict(candidate)
            if extracted:
                return extracted
        return None

    try:
        tools = create_mcp_browser_tools()
        if not tools:
            print("Browser MCP tools are unavailable; nothing to run.")
            return

        try:
            model = get_chat_model(settings)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to initialise chat model: {exc}")
            return

        agent = create_react_agent(model, tools, version="v1")

        print("Running ReAct agent against heise.de ...", flush=True)
        user_message = HumanMessage(content=USER_PROMPT)
        final_state: Optional[Dict[str, Any]] = None

        last_assistant_text: Optional[str] = None

        try:
            async for event in agent.astream_events(
                {"messages": [user_message]},
                version="v1",
            ):
                kind = event.get("event")
                data: Dict[str, Any] = event.get("data", {})

                if kind == "on_chat_model_end":
                    output = data.get("output", {})
                    generations = output.get("generations", []) if isinstance(output, dict) else []
                    if generations and generations[0]:
                        generation = generations[0][0]
                        message = generation.get("message") if isinstance(generation, dict) else None
                        content = None
                        if isinstance(message, dict):
                            content = message.get("content")
                        elif isinstance(message, AIMessage):
                            content = message.content
                        if content:
                            print("\nLLM reasoning:\n" + str(content))
                            if isinstance(content, str):
                                last_assistant_text = content
                elif kind == "on_tool_start":
                    name = _extract_tool_name(event)
                    tool_input = data.get("input") or {}
                    metadata = event.get("metadata")
                    if not isinstance(metadata, dict):
                        metadata = {}
                    call_id = data.get("id") or data.get("tool_call_id")
                    if not call_id and isinstance(metadata, dict):
                        call_id = metadata.get("tool_call_id")
                    call_suffix = f" [id={call_id}]" if call_id else ""
                    if not name:
                        print(f"\n→ Tool call{call_suffix} (raw): {_preview(data)}")
                    else:
                        print(f"\n→ Tool {name}{call_suffix} called with {_preview(tool_input)}")
                elif kind == "on_tool_end":
                    name = _extract_tool_name(event)
                    output = data.get("output")
                    display_name = name or "<unknown>"

                    if name is None and hasattr(output, "name"):
                        # ToolMessage or similar from LangChain
                        name = getattr(output, "name", None)
                        display_name = name or display_name

                    if hasattr(output, "name") and not name:
                        name = getattr(output, "name", None)
                        display_name = name or display_name

                    print(f"← Tool {display_name} result {_preview(output)}")

                    if name == "research_extract_structured_data" and output is not None:
                        html_snippet = None
                        if hasattr(output, "content"):
                            content = output.content
                            if isinstance(content, str):
                                try:
                                    payload = json.loads(content)
                                    html_snippet = payload.get("html")
                                except json.JSONDecodeError:
                                    html_snippet = content
                        if html_snippet:
                            snippet = html_snippet[:400] + ("…" if len(html_snippet) > 400 else "")
                            print("\n[page content preview]\n" + snippet)
                elif kind == "on_run_end":
                    final_state = data.get("output")  # type: ignore[assignment]
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    lg_output = data.get("output")
                    if isinstance(lg_output, dict):
                        final_state = lg_output
        except asyncio.TimeoutError:
            print("Agent run timed out after 180s.")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"Agent execution failed: {exc}")
            return

        if not final_state:
            print("Agent did not return a final state.")
            return

        raw_messages = final_state.get("messages", []) if isinstance(final_state, dict) else []

        def _as_ai_message(message: Any) -> Optional[str]:
            if isinstance(message, AIMessage):
                return message.content
            if isinstance(message, BaseMessage) and getattr(message, "type", "") == "ai":
                return getattr(message, "content", "")
            if isinstance(message, dict):
                if message.get("role") == "assistant":
                    content = message.get("content")
                    if isinstance(content, list):
                        parts = [
                            chunk.get("text", "")
                            for chunk in content
                            if isinstance(chunk, dict) and chunk.get("type") == "text"
                        ]
                        return "\n".join(part for part in parts if part)
                    if isinstance(content, str):
                        return content
            return None

        final_text: Optional[str] = None
        for msg in reversed(raw_messages):
            maybe_text = _as_ai_message(msg)
            if maybe_text:
                final_text = maybe_text
                break

        if not final_text and last_assistant_text:
            final_text = last_assistant_text

        if not final_text:
            print("Agent completed without a final assistant message.")
            return

        print("\n=== Agent Final Response ===\n")
        print(final_text)
    finally:
        await shutdown_mcp_browser()


if __name__ == "__main__":
    asyncio.run(run())
