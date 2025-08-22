"""Learning Agent state schema extending DeepAgentState."""

from typing import Annotated, Any, Literal, NotRequired

from deepagents import DeepAgentState
from pydantic import BaseModel, Field


class Memory(BaseModel):
    """A single memory from past execution."""

    id: str
    task: str
    context: str | None
    narrative: str
    reflection: str
    outcome: Literal["success", "failure"]
    timestamp: str
    embedding: list[float] | None = None


class Pattern(BaseModel):
    """A learned pattern from multiple experiences."""

    id: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    success_rate: float = Field(ge=0.0, le=1.0)
    applications: int = 0
    last_used: str | None = None


class ExecutionData(BaseModel):
    """Data from a task execution for learning."""

    task: str
    context: str | None
    outcome: Literal["success", "failure"]
    duration: float
    description: str
    error: str | None


def memory_reducer(left: list[Memory] | None, right: list[Memory] | None) -> list[Memory]:
    """Reducer for memories - appends new memories."""
    if left is None:
        return right if right is not None else []
    if right is None:
        return left
    # Append new memories, avoiding duplicates by ID
    existing_ids = {m.id for m in left}
    new_memories = [m for m in right if m.id not in existing_ids]
    return left + new_memories


def pattern_reducer(left: list[Pattern] | None, right: list[Pattern] | None) -> list[Pattern]:
    """Reducer for patterns - merges and updates patterns."""
    if left is None:
        return right if right is not None else []
    if right is None:
        return left

    # Merge patterns by ID, taking the most recent version
    pattern_dict = {p.id: p for p in left}
    for pattern in right:
        pattern_dict[pattern.id] = pattern
    return list(pattern_dict.values())


def learning_queue_reducer(
    left: list[ExecutionData] | None, right: list[ExecutionData] | None
) -> list[ExecutionData]:
    """Reducer for learning queue - appends new items."""
    if left is None:
        return right if right is not None else []
    if right is None:
        return left
    return left + right


class LearningAgentState(DeepAgentState):  # type: ignore[misc]
    """Extended state for learning agent with memory and pattern tracking."""

    # Learning-specific state
    memories: NotRequired[Annotated[list[Memory], memory_reducer]]  # type: ignore[valid-type]
    patterns: NotRequired[Annotated[list[Pattern], pattern_reducer]]  # type: ignore[valid-type]
    current_context: NotRequired[dict[str, Any]]  # type: ignore[valid-type]
    learning_queue: NotRequired[Annotated[list[ExecutionData], learning_queue_reducer]]  # type: ignore[valid-type]

    # Quick context for current task
    relevant_memories: NotRequired[list[str]]  # type: ignore[valid-type]
    applicable_patterns: NotRequired[list[str]]  # type: ignore[valid-type]
