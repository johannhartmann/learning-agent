"""Unit tests for helper utilities in learning_agent.agent."""

from langchain_core.messages import AIMessage

from learning_agent.stream_adapter import coerce_to_dict, StreamAdapter


class DummyBase:
    def __init__(self) -> None:
        self.value = 42


class DummyGeneration:
    def __init__(self, message: AIMessage) -> None:
        self.message = message


class DummyOutput:
    def __init__(self, message: AIMessage) -> None:
        self.generations = [[DummyGeneration(message)]]


class DummyEventPayload:
    def __init__(self, message: AIMessage) -> None:
        self.output = DummyOutput(message)


def test_coerce_to_dict_keeps_mapping_values() -> None:
    """Mappings are returned unchanged."""

    mapping = {"foo": "bar"}
    assert coerce_to_dict(mapping) == mapping


def test_coerce_to_dict_handles_ai_message() -> None:
    """AIMessage objects are converted into plain dicts without error."""

    msg = AIMessage(content="hello")
    result = coerce_to_dict(msg)

    assert result.get("content") == "hello"


def test_coerce_to_dict_handles_nested_payload() -> None:
    """Objects with __dict__ attributes are converted to dictionaries."""

    msg = AIMessage(content="hi there")
    payload = DummyEventPayload(msg)

    as_dict = coerce_to_dict(payload)

    assert "output" in as_dict
    assert hasattr(as_dict["output"], "generations")


def test_stream_adapter_begin_and_complete_emit_envelope() -> None:
    """StreamAdapter emits deterministic start/end envelopes."""

    events: list[dict[str, object]] = []
    adapter = StreamAdapter(events.append, agent_label="test-agent", profile="debug")

    adapter.begin({"foo": "bar"})
    adapter.complete({"messages": []})

    assert len(events) == 2
    assert events[0]["type"] == "tool_start"
    assert events[0]["event"] == "start"
    assert events[1]["type"] == "tool_end"
    assert events[1]["event"] == "finish"
    assert events[0]["call_id"] == events[1]["call_id"]


def test_stream_adapter_accept_emits_token_events() -> None:
    """LangGraph LLM token events are converted to llm_token envelopes."""

    events: list[dict[str, object]] = []
    adapter = StreamAdapter(events.append, agent_label="agent", profile="debug")
    adapter.begin({"input": "hi"})

    adapter.accept(
        {
            "event": "on_chat_model_stream",
            "name": "llm",
            "data": {"token": "hello"},
        }
    )
    adapter.complete({"messages": []})

    token_events = [ev for ev in events if ev["type"] == "llm_token"]
    assert token_events
    assert token_events[0]["payload"]["text"] == "hello"
    assert token_events[0]["event"] == "llm_token"
