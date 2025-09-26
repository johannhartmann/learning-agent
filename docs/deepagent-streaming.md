# DeepAgents & LangGraph Streaming: Integration Considerations

This note captures the **general tension** between DeepAgents' runtime model and
LangGraph's structured streaming. It also codifies the target architecture for a
single streaming bridge so DeepAgents, LangGraph, and deepagents-ui can evolve
independently while sharing one stable event contract.

## Execution Models in Brief

| Concern | DeepAgents (today) | LangGraph (v0.2+) |
| --- | --- | --- |
| Concurrency | Cooperative via async tools; one logical REAct loop | Graph of nodes with explicit concurrency primitives & checkpoints |
| Tool Interface | LangChain `BaseTool` returning Python values | LangChain-style tools embedded in a graph, streamed as structured events |
| State Container | Pydantic model (`DeepAgentState`) merged via reducers | `StateGraph` dictionaries serialized via checkpointers |
| Streaming Contract | Optional; tooling expects dict payloads | Strongly typed event stream (Pydantic models, nested objects) |

The production topology places a DeepAgents REAct agent at the root of a
LangGraph graph and delegates work to nested LangGraph subgraphs. Two distinct
assumptions about streaming/state must therefore be reconciled.

## Target Architecture

```
LangGraph (structured events)
     │  on_* callbacks / event stream
     ▼
[ StreamAdapter ]
  - coerce shape
  - map event types
  - synthesize completion
  - throttle/sample
  - assign IDs/seq
     │  normalized UI events (stable schema)
     ▼
 deepagents-ui  (collapsible subcalls, progress, files, tokens)
```

A **StreamAdapter** module owns coercion, mapping, completion signals, and
backpressure. Everything that enters or leaves LangGraph flows through this
adapter so the UI consumes a single, framework-agnostic envelope.

## Stable Event Envelope

Adapters emit a uniform JSON payload so the UI can render nested progress without
knowing whether the underlying run came from LangGraph, LangChain, or replays.

```json
{
  "type": "llm_token | llm_start | llm_end | tool_start | tool_update | tool_end | subgraph_checkpoint | subgraph_resume | warning | error",
  "ts": 1732545858.123,
  "trace_id": "root-trace-uuid",
  "run_id": "langgraph-run-id",
  "parent_id": "call-uuid",
  "call_id": "call-uuid",
  "seq": 42,
  "origin": "live | replay",
  "agent": "researcher",
  "payload": { /* framework-specific details */ }
}
```

- `trace_id`: ties the entire request together.
- `call_id`: unique per subgraph/tool invocation; reused on replay.
- `parent_id`: links nested calls to their parents.
- `seq`: monotonically increasing per `call_id` → deterministic re-rendering.
- `origin`: distinguishes live emission from replayed checkpoints.

## Event Mapping Cheat Sheet

| LangGraph event                       | Envelope `type`        | Required payload fields                                   |
|---------------------------------------|------------------------|------------------------------------------------------------|
| `on_chain_start` (subgraph)           | `tool_start`           | `tool_name` (graph id), `input`, optional `meta`           |
| `on_chain_end` (subgraph)             | `tool_end`             | `tool_name`, `result` (normalised state)                   |
| `on_chat_model_start`                 | `llm_start`            | `model`, `params`, optional `node`                         |
| `on_chat_model_stream`/`*_token`      | `llm_token`            | `text`, optional `logprob`                                 |
| `on_chat_model_end`                   | `llm_end`              | `usage`, `finish_reason`                                   |
| `on_tool_start`                       | `tool_start`           | `tool_name`, `args`, `node`                                |
| `on_tool_end`                         | `tool_end`             | `tool_name`, `result`                                      |
| `on_chain_error` / `on_tool_error`    | `error`                | `name`, `message`, `stack`, `class`                        |
| checkpoint persisted                  | `subgraph_checkpoint`  | `checkpoint_id`, `node`, `state_digest`                    |
| checkpoint resume                     | `subgraph_resume`      | `checkpoint_id`, `node`                                    |

IDs must be stable across retries. Each subgraph receives a `call_id`; nested
LangGraph tools inherit that as `parent_id` and maintain their own `seq` counter.

## Friction Points & Design Rules

### 1. Payload Shape Mismatch → Central Coercion

LangGraph emits nested Pydantic objects (`AIMessage`, `LLMResult`, `ToolMessage`),
while DeepAgents historically expected dicts. Every stream entry must therefore
pass through a coercion helper housed in the adapter.

```python
def coerce_to_dict(obj: Any) -> dict[str, Any]:
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
            return json.loads(to_json())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    if isinstance(obj, (bytes, bytearray)):
        return {"text": obj.decode(errors="replace")}
    if isinstance(obj, str):
        return {"text": obj}
    return {"repr": repr(obj)}
```

Apply this helper to every `on_*` payload before further processing; new wrapper
classes introduced by LangGraph upgrades then become an additive change.

### 2. Completion Signalling → Deterministic Normalisation

- Treat `on_chain_end` as the authoritative completion point for subgraphs.
- Normalise outputs into `{ "messages": [...], "files": {...}, "usage": {...} }`.
- If the UI (e.g. MCP browser) expects explicit `research_done` signals, synthesize
  `tool_start/tool_end` events around the normalised result.

### 3. Checkpointing vs Mutable State → Reducers Only

LangGraph checkpoints the state dictionary; DeepAgents mutates objects. Restrict
mutations to reducer-friendly deltas (e.g. append to `files.added`). Tag replayed
emissions with `origin="replay"` and reuse the same `call_id`/`seq` so the UI can
render rehydrated history without duplicating live events.

### 4. Backpressure → Profiles & Sampling

- Batch LLM tokens within 25–75 ms windows and rate-limit tool updates per
  `call_id`.
- Never drop `*_start/*_end` events.
- Offer profiles such as `debug` (no sampling) and `user` (tokens coalesced,
  trimmed tool logs).

## Adapter Skeleton

```python
class StreamAdapter:
    def __init__(self, emitter, profile="user"):
        self.emitter = emitter
        self.profile = profile
        self._seq = collections.defaultdict(lambda: itertools.count(1))
        self._sampler = EventSampler(emitter, profile)

    def _envelope(self, *, type_, trace_id, run_id, parent_id, call_id, payload, origin="live"):
        return {
            "type": type_,
            "ts": time.time(),
            "trace_id": trace_id,
            "run_id": run_id,
            "parent_id": parent_id,
            "call_id": call_id,
            "seq": next(self._seq[call_id]),
            "origin": origin,
            "payload": payload,
        }

    async def adapt(self, events: AsyncIterator[dict[str, Any]], label: str) -> None:
        call_id = str(uuid.uuid4())
        trace_id = call_id
        run_id: str | None = None
        parent_id: str | None = None

        async for raw in events:
            kind = raw.get("event") or raw.get("type")
            data = coerce_to_dict(raw)
            run_id = run_id or data.get("run_id") or data.get("id")

            if kind == "on_chain_start":
                self._sampler.push(self._envelope(
                    type_="tool_start",
                    trace_id=trace_id,
                    run_id=run_id,
                    parent_id=parent_id,
                    call_id=call_id,
                    payload={"tool_name": label, "input": data.get("inputs")},
                ))
            # … map remaining events per the table above …
```

The adapter hands events to an `EventSampler` that coalesces tokens, rate-limits
logs, and flushes at least every 250 ms to keep the UI responsive.

## Recommended Engineering Practices

1. **Centralise Adaptation** – Keep coercion, mapping, completion, and sampling in
   one module (e.g. `stream_adapter.py`). Unit tests should cover representative
   LangGraph payloads as in `tests/test_agent_helpers.py`.
2. **Assert Contracts in CI** – Maintain golden JSONL streams for nested runs and
   assert the adapter produces the expected envelope sequence.
3. **Document Subgraph Semantics** – Each subgraph should publish the shape of its
   final state so the normaliser is not guessing.
4. **Monitor Runtime** – Alerts on unusually long LangSmith traces highlight cases
   where the adapter failed to emit completion signals.

By codifying these architectural invariants—and routing all streaming through the
adapter—we avoid one-off fixes, support deterministic replays, and keep the UI
agnostic to internal framework churn.
