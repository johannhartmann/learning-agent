"""Tests for learning relevance signal detection."""

from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from learning_agent.learning.langmem_integration import compute_learning_relevance_signals


def test_compute_learning_relevance_signals_requires_signal() -> None:
    """Without progress signals the helper returns an empty list."""

    messages = [HumanMessage(content="hi"), AIMessage(content="hello")]
    signals = compute_learning_relevance_signals(messages, metadata={}, execution_analysis={})

    assert signals == []


def test_compute_learning_relevance_signals_detects_tool_usage() -> None:
    """Tool interactions surface as relevance signals."""

    tool_message = SimpleNamespace(type="tool")
    messages = [HumanMessage(content="hi"), tool_message]
    execution_analysis = {"total_tool_calls": 2}

    signals = compute_learning_relevance_signals(
        messages=messages,
        metadata={},
        execution_analysis=execution_analysis,
    )

    assert "tool_usage" in signals
    assert "tool_messages" in signals


def test_compute_learning_relevance_signals_detects_task_progress() -> None:
    """Completed todos propagate to relevance signals."""

    metadata = {
        "completed_count": 1,
        "todos": [
            {"title": "step1", "status": "completed"},
            {"title": "step2", "status": "pending"},
        ],
    }

    signals = compute_learning_relevance_signals(
        messages=[HumanMessage(content="hi")],
        metadata=metadata,
        execution_analysis={"total_tool_calls": 0},
    )

    assert "completed_tasks" in signals
    assert "todo_progress" in signals


def test_compute_learning_relevance_signals_detects_failure_metadata() -> None:
    """Failure metadata keeps the learning pipeline engaged."""

    metadata = {
        "type": "task_execution",
        "outcome": "failure",
        "has_error": True,
        "error": "Traceback...",
    }

    signals = compute_learning_relevance_signals(
        messages=[AIMessage(content="failed")],
        metadata=metadata,
        execution_analysis={},
    )

    assert "task_execution_event" in signals
    assert "failure_outcome" in signals
    assert "execution_error" in signals
    assert "reported_error" in signals

