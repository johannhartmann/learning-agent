"""Learning-specific tools for the deepagents-based learning agent."""

from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from learning_agent.state import ExecutionData, LearningAgentState, Memory, Pattern


@tool
def search_memory(
    query: str,
    state: Annotated[LearningAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Any]:
    """Search past experiences using semantic similarity.

    Args:
        query: The search query describing what kind of past experience to find

    Returns:
        Command with relevant memories and patterns
    """
    # Get existing memories from state
    memories = state.get("memories", [])
    patterns = state.get("patterns", [])

    # Simple text-based search for now (will be enhanced with semantic search)
    relevant_memories = []
    applicable_patterns = []

    query_lower = query.lower()

    # Search memories
    relevant_memories = [
        f"Task: {memory.task}\nOutcome: {memory.outcome}\nNarrative: {memory.narrative[:200]}..."
        for memory in memories
        if (
            query_lower in memory.task.lower()
            or query_lower in memory.narrative.lower()
            or query_lower in memory.reflection.lower()
        )
    ]

    # Search patterns
    applicable_patterns = [
        f"Pattern: {pattern.description} (confidence: {pattern.confidence:.2f})"
        for pattern in patterns
        if query_lower in pattern.description.lower() and pattern.confidence > 0.7
    ]

    # Prepare response
    if relevant_memories or applicable_patterns:
        response = "Found relevant past experiences:\n\n"

        if relevant_memories:
            response += "**Past Experiences:**\n" + "\n".join(relevant_memories[:3]) + "\n\n"

        if applicable_patterns:
            response += "**Applicable Patterns:**\n" + "\n".join(applicable_patterns[:3])
    else:
        response = f"No relevant past experiences found for: {query}"

    return Command(
        update={
            "relevant_memories": relevant_memories[:3],
            "applicable_patterns": applicable_patterns[:3],
            "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
        }
    )


@tool
def queue_learning(
    task: str,
    outcome: str,
    description: str,
    state: Annotated[LearningAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    duration: float = 0.0,
    context: str | None = None,
    error: str | None = None,
) -> Command[Any]:
    """Queue a task execution for background learning.

    Args:
        task: The task that was executed
        outcome: 'success' or 'failure'
        description: Description of what happened
        duration: How long the task took
        context: Additional context about the execution
        error: Error message if the task failed
    """
    # Create execution data for learning
    execution_data = ExecutionData(
        task=task,
        context=context,
        outcome=outcome,  # type: ignore
        duration=duration,
        description=description,
        error=error,
    )

    # Get existing queue
    current_queue = state.get("learning_queue", [])
    updated_queue = [*current_queue, execution_data]

    return Command(
        update={
            "learning_queue": updated_queue,
            "messages": [
                ToolMessage(
                    f"Queued '{task}' ({outcome}) for background learning",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


@tool
def apply_pattern(
    pattern_description: str,
    state: Annotated[LearningAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Any]:
    """Apply a learned pattern to the current task.

    Args:
        pattern_description: Description of the pattern to apply
    """
    patterns = state.get("patterns", [])

    # Find matching pattern
    matching_pattern = None
    for pattern in patterns:
        if pattern_description.lower() in pattern.description.lower():
            matching_pattern = pattern
            break

    if matching_pattern and matching_pattern.confidence > 0.8:
        # Update pattern usage
        matching_pattern.applications += 1
        matching_pattern.last_used = datetime.now().isoformat()

        # Update patterns in state
        updated_patterns = [
            p if p.id != matching_pattern.id else matching_pattern for p in patterns
        ]

        response = f"Applied high-confidence pattern: {matching_pattern.description}\n"
        response += f"Success rate: {matching_pattern.success_rate:.2%}, Applications: {matching_pattern.applications}"

        return Command(
            update={
                "patterns": updated_patterns,
                "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
            }
        )
    response = f"No high-confidence pattern found for: {pattern_description}"

    return Command(
        update={
            "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
        }
    )


@tool
def create_memory(
    task: str,
    narrative: str,
    reflection: str,
    outcome: str,
    state: Annotated[LearningAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    context: str | None = None,
) -> Command[Any]:
    """Create a new memory from a task execution.

    Args:
        task: The task that was executed
        narrative: A story-like narrative of the experience
        reflection: Deep reflection on the experience
        outcome: 'success' or 'failure'
        context: Additional context about the execution
    """
    # Create new memory
    memory = Memory(
        id=str(uuid4()),
        task=task,
        context=context,
        narrative=narrative,
        reflection=reflection,
        outcome=outcome,  # type: ignore
        timestamp=datetime.now().isoformat(),
    )

    # Get existing memories and add new one
    current_memories = state.get("memories", [])
    updated_memories = [*current_memories, memory]

    return Command(
        update={
            "memories": updated_memories,
            "messages": [
                ToolMessage(f"Created memory for task: {task}", tool_call_id=tool_call_id)
            ],
        }
    )


@tool
def create_pattern(
    description: str,
    confidence: float,
    success_rate: float,
    state: Annotated[LearningAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Any]:
    """Create a new learned pattern.

    Args:
        description: Description of the pattern
        confidence: Confidence level (0.0 to 1.0)
        success_rate: Success rate of this pattern (0.0 to 1.0)
    """
    # Create new pattern
    pattern = Pattern(
        id=str(uuid4()),
        description=description,
        confidence=max(0.0, min(1.0, confidence)),
        success_rate=max(0.0, min(1.0, success_rate)),
        applications=0,
    )

    # Get existing patterns and add new one
    current_patterns = state.get("patterns", [])
    updated_patterns = [*current_patterns, pattern]

    return Command(
        update={
            "patterns": updated_patterns,
            "messages": [
                ToolMessage(
                    f"Created pattern: {description} (confidence: {confidence:.2f})",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


def create_learning_tools() -> list[BaseTool]:
    """Create all learning-specific tools for the deepagents agent."""
    return [
        search_memory,
        queue_learning,
        apply_pattern,
        create_memory,
        create_pattern,
    ]
