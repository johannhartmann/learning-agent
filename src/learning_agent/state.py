"""Learning Agent state schema extending DeepAgentState."""

import operator
from typing import Annotated, Any, Literal, NotRequired

from deepagents import DeepAgentState
from pydantic import BaseModel


class ExecutionData(BaseModel):
    """Data from a task execution for learning."""

    task: str
    context: str | None
    outcome: Literal["success", "failure"]
    duration: float
    description: str
    error: str | None


class LearningAgentState(DeepAgentState):  # type: ignore[misc]
    """Extended state for learning agent.

    All memories and patterns are stored in PostgreSQL.
    State only tracks current task context and temporary data.
    """

    # Current task context
    current_context: NotRequired[dict[str, Any]]  # type: ignore[valid-type]

    # Temporary learning queue (could be removed if we process immediately)
    learning_queue: NotRequired[list[ExecutionData]]  # type: ignore[valid-type]

    # Quick access to search results for current task
    relevant_learnings: NotRequired[list[str]]  # type: ignore[valid-type]

    # Track recent sandbox execution errors to avoid repeating failures
    # Use Annotated with operator.add to handle concurrent updates
    sandbox_error_history: NotRequired[Annotated[list[dict[str, str]], operator.add]]  # type: ignore[valid-type]

    # Inherit `files` aggregation behavior from DeepAgentState (file_reducer merges dicts)

    # Current session's learning data for UI display
    memories: NotRequired[list[dict[str, Any]]]  # type: ignore[valid-type]
    patterns: NotRequired[list[dict[str, Any]]]  # type: ignore[valid-type]

    # Optional fields produced by downstream nodes/tools that aren't part of the core schema
    # Adding them here avoids "unknown channel" warnings in LangGraph when nodes pass state through
    remaining_steps: NotRequired[int]  # type: ignore[valid-type]
    thread_id: NotRequired[str]  # type: ignore[valid-type]
