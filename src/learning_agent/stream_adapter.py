"""Streaming bridge between LangGraph events, DeepAgents, and the UI."""

from __future__ import annotations

import collections
import itertools
import json
import time
import uuid
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any


StreamEvent = dict[str, Any]


def coerce_to_dict(obj: Any) -> dict[str, Any]:
    """Best-effort conversion of LangChain / LangGraph payloads to a dict."""

    if obj is None:
        return {}

    if isinstance(obj, Mapping):
        return dict(obj)

    for attr in ("model_dump", "dict"):
        method = getattr(obj, attr, None)
        if callable(method):
            try:
                result = method()
            except Exception:
                continue
            if isinstance(result, Mapping):
                return dict(result)

    to_json = getattr(obj, "to_json", None)
    if callable(to_json):
        try:
            text = to_json()
        except Exception:
            text = None
        if isinstance(text, str):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {"text": text}
            if isinstance(data, Mapping):
                return dict(data)

    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}

    if isinstance(obj, bytes | bytearray):
        try:
            return {"text": obj.decode(errors="replace")}
        except Exception:
            return {"repr": repr(obj)}

    if isinstance(obj, str):
        return {"text": obj}

    return {"repr": repr(obj)}


class EventSampler:
    """Coalesce noisy streaming events before emitting to the UI."""

    def __init__(
        self,
        sink: Callable[[StreamEvent], None],
        *,
        profile: str = "user",
        window_ms: int = 50,
        max_token_chars: int = 512,
    ) -> None:
        self._sink = sink
        self._profile = profile
        self._window = window_ms / 1000.0
        self._max_chars = max_token_chars
        self._token_buffers: dict[str, StreamEvent] = {}
        self._deadlines: dict[str, float] = {}

    def push(self, event: StreamEvent) -> None:
        """Add an event to the sampler, flushing as required."""

        if self._profile == "debug" or event.get("type") != "llm_token":
            self.flush_tokens(event.get("call_id"))
            self._sink(event)
            return

        call_id = event.get("call_id")
        if call_id is None:
            self._sink(event)
            return

        payload = event.get("payload") or {}
        text = payload.get("text", "")
        if not text:
            return

        pending = self._token_buffers.get(call_id)
        now = time.monotonic()
        if pending is None:
            self._token_buffers[call_id] = dict(event)
            self._token_buffers[call_id]["payload"] = {"text": text}
            self._deadlines[call_id] = now + self._window
            return

        pending_payload = pending.setdefault("payload", {})
        pending_payload["text"] = pending_payload.get("text", "") + text
        pending["ts"] = event.get("ts", time.time())

        deadline = self._deadlines.get(call_id, now)
        if len(pending_payload.get("text", "")) >= self._max_chars or now >= deadline:
            self.flush_tokens(call_id)

    def flush_tokens(self, call_id: str | None = None) -> None:
        """Flush buffered token events."""

        if call_id is not None:
            pending = self._token_buffers.pop(call_id, None)
            self._deadlines.pop(call_id, None)
            if pending:
                self._sink(pending)
            return

        for cid in list(self._token_buffers):
            self.flush_tokens(cid)


class StreamAdapter:
    """Normalize LangGraph events into a stable envelope for the UI."""

    def __init__(
        self,
        emit: Callable[[StreamEvent], None],
        *,
        agent_label: str,
        trace_id: str | None = None,
        parentMessageId: str | None = None,  # noqa: N803
        profile: str = "user",
    ) -> None:
        self._emit = emit
        self._agent_label = agent_label
        self._trace_id = trace_id or str(uuid.uuid4())
        self._parent_message_id = parentMessageId
        self._root_call_id = str(uuid.uuid4())
        self._profile = profile
        self._sampler = EventSampler(self._emit, profile=profile)
        self._seq: dict[str, itertools.count[int]] = collections.defaultdict(
            lambda: itertools.count(1)
        )
        self._child_calls: dict[str, str] = {}
        self._run_id: str | None = None
        self._event_log: list[str] = []
        self._structured_content: list[str] = []

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def call_id(self) -> str:
        return self._root_call_id

    def _envelope(
        self,
        *,
        type_: str,
        call_id: str,
        payload: dict[str, Any],
        parentMessageId: str | None = None,  # noqa: N803
        origin: str = "live",
        event_name: str | None = None,
    ) -> StreamEvent:
        resolved_parent = (
            parentMessageId if parentMessageId is not None else self._parent_message_id
        )
        event = {
            "type": type_,
            "ts": time.time(),
            "trace_id": self._trace_id,
            "run_id": self._run_id,
            "parentMessageId": resolved_parent,
            "call_id": call_id,
            "seq": next(self._seq[call_id]),
            "origin": origin,
            "agent": self._agent_label,
            "payload": payload,
        }
        event["event"] = event_name or type_
        event["subagent"] = self._agent_label

        tool_name = payload.get("tool_name") if isinstance(payload, dict) else None
        if isinstance(tool_name, str) and tool_name:
            event["tool"] = tool_name

        if type_ == "llm_token":
            token_text = payload.get("text") if isinstance(payload, dict) else None
            if token_text is not None:
                event["token"] = token_text

        if type_ == "warning":
            message_text = payload.get("message") if isinstance(payload, dict) else None
            if message_text is not None:
                event["message"] = message_text

        return event

    def begin(self, inputs: dict[str, Any]) -> None:
        """Emit the opening event for the sub-agent."""

        payload = {"tool_name": self._agent_label, "input": inputs}
        start_event = self._envelope(
            type_="tool_start",
            call_id=self._root_call_id,
            payload=payload,
            parentMessageId=self._parent_message_id,
            event_name="start",
        )
        self._sampler.push(start_event)
        description = inputs.get("description") if isinstance(inputs, dict) else None
        if description:
            self._event_log.append(f"Delegated to {self._agent_label}: {description}")

    def accept(self, event: dict[str, Any]) -> None:
        """Process a LangGraph streaming event."""

        kind = event.get("event") or event.get("type")
        name = event.get("name")
        data = coerce_to_dict(event.get("data"))
        self._run_id = self._run_id or event.get("run_id") or data.get("run_id")

        if kind == "on_chat_model_start":
            model = data.get("model_name") or data.get("name") or name
            payload = {
                "model": model,
                "params": data.get("invocation_params") or data.get("config") or {},
            }
            envelope = self._envelope(
                type_="llm_start",
                call_id=self._root_call_id,
                payload=payload,
            )
            self._sampler.push(envelope)
            return

        if kind in {"on_chat_model_stream", "on_llm_new_token", "on_chat_model_delta"}:
            text = data.get("token") or data.get("text") or data.get("content") or ""
            if text:
                payload = {"text": text}
                envelope = self._envelope(
                    type_="llm_token",
                    call_id=self._root_call_id,
                    payload=payload,
                )
                self._sampler.push(envelope)
            return

        if kind == "on_chat_model_end":
            payload = {
                "usage": data.get("usage") or {},
                "finish_reason": data.get("finish_reason"),
            }
            envelope = self._envelope(
                type_="llm_end",
                call_id=self._root_call_id,
                payload=payload,
            )
            self._sampler.push(envelope)
            return

        if kind == "on_tool_start":
            key = data.get("id") or event.get("run_id") or f"{name}:{uuid.uuid4()}"
            call_id = self._child_calls.setdefault(key, str(uuid.uuid4()))
            payload = {
                "tool_name": name or data.get("name"),
                "args": data.get("input") or data.get("tool_input") or {},
            }
            envelope = self._envelope(
                type_="tool_start",
                call_id=call_id,
                payload=payload,
            )
            self._sampler.push(envelope)
            tool_display = payload.get("tool_name") or "tool"
            self._event_log.append(f"→ {tool_display} start")
            return

        if kind == "on_tool_end":
            key = data.get("id") or event.get("run_id") or f"{name}:{uuid.uuid4()}"
            call_id = self._child_calls.pop(key, str(uuid.uuid4()))
            tool_name = name or data.get("name")
            result = coerce_to_dict(data.get("output"))
            payload = {
                "tool_name": tool_name,
                "result": result,
            }
            envelope = self._envelope(
                type_="tool_end",
                call_id=call_id,
                payload=payload,
            )
            self._sampler.push(envelope)

            result_envelope = self._envelope(
                type_="tool_result",
                call_id=call_id,
                payload={
                    "tool_name": tool_name,
                    "result": result,
                },
                event_name="tool_result",
            )
            self._sampler.push(result_envelope)

            tool_display = tool_name or "tool"
            if tool_display == "research_extract_structured_data":
                content = result.get("content")
                if isinstance(content, str):
                    self._structured_content.append(content)
            snippet = result.get("text") or result.get("content") or ""
            if snippet:
                snippet = snippet[:160]
            self._event_log.append(
                f"← {tool_display} complete" + (f": {snippet}" if snippet else "")
            )
            return

        if kind in {"on_tool_error", "on_chain_error"}:
            payload = {
                "name": name,
                "message": data.get("error") or data.get("message"),
                "stack": data.get("stack"),
                "class": data.get("error_type") or data.get("type"),
            }
            envelope = self._envelope(
                type_="error",
                call_id=self._root_call_id,
                parentMessageId=self._parent_message_id,
                payload=payload,
                event_name="error",
            )
            self._sampler.flush_tokens()
            self._sampler.push(envelope)
            message = payload.get("message") or payload.get("name") or "error"
            self._event_log.append(f"⚠ {message}")

    def emit_warning(self, message: str) -> None:
        envelope = self._envelope(
            type_="warning",
            call_id=self._root_call_id,
            parentMessageId=self._parent_message_id,
            payload={"message": message},
            event_name="warning",
        )
        self._sampler.push(envelope)
        self._event_log.append(f"⚠ {message}")

    def complete(self, result: dict[str, Any], *, status: str = "success") -> None:
        """Flush token buffers and emit the final tool_end event."""

        self._sampler.flush_tokens()
        payload = {
            "tool_name": self._agent_label,
            "status": status,
            "result": result,
        }
        end_event = self._envelope(
            type_="tool_end",
            call_id=self._root_call_id,
            parentMessageId=self._parent_message_id,
            payload=payload,
            event_name="tool_end" if status != "success" else "finish",
        )
        self._sampler.push(end_event)

    def emit_synthetic_completion(
        self, tool_name: str, result: dict[str, Any] | None = None
    ) -> None:
        """Emit a synthetic start/end pair for tools that never surfaced."""

        call_id = str(uuid.uuid4())
        start = self._envelope(
            type_="tool_start",
            call_id=call_id,
            payload={"tool_name": tool_name, "synthetic": True},
            event_name="tool_start",
        )
        end = self._envelope(
            type_="tool_end",
            call_id=call_id,
            payload={"tool_name": tool_name, "synthetic": True, "result": result or {}},
            event_name="tool_end",
        )
        self._sampler.push(start)
        self._sampler.push(end)

    async def adapt(self, events: AsyncIterator[dict[str, Any]]) -> None:
        """Consume an async iterator of LangGraph events."""

        async for event in events:
            self.accept(event)
        self._sampler.flush_tokens()

    def get_transcript(self) -> str:
        return "\n".join(entry for entry in self._event_log if entry)

    def get_structured_content(self) -> list[str]:
        return list(self._structured_content)
