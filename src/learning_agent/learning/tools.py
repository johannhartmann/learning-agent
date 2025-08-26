"""Learning-specific tools for the deepagents-based learning agent."""

from typing import Annotated, Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from learning_agent.state import ExecutionData, LearningAgentState


@tool
async def search_memory(
    task: str,
    state: Annotated[LearningAgentState, InjectedState],  # noqa: ARG001
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Any]:
    """Find learnings from similar past tasks.

    Args:
        task: The current task to find similar past tasks and their learnings for

    Returns:
        Command with learnings from similar tasks
    """
    # Import here to avoid circular imports
    from learning_agent.learning.langmem_integration import get_learning_system

    # Get learning system and search for similar tasks
    learning_system = get_learning_system()
    similar_task_learnings = await learning_system.search_similar_tasks(task, limit=5)

    # TODO: In future, fetch patterns from PostgreSQL patterns table
    # For now, we'll skip pattern checking since we're removing in-memory patterns
    applicable_patterns: list[str] = []

    # Prepare response with rich learning dimensions
    response = f"Learnings from similar tasks for: '{task}'\n\n"

    if similar_task_learnings:
        response += "**Similar Task Learnings:**\n"
        for idx, item in enumerate(similar_task_learnings[:3], 1):
            response += f"\n{idx}. **Task**: {item['similar_task']} (Similarity: {item['similarity']:.1%})\n"
            response += f"   **Outcome**: {item['outcome']}\n"

            # Include tactical learning if present
            if item.get("tactical_learning"):
                response += f"   **Tactical**: {item['tactical_learning'][:200]}...\n"

            # Include strategic learning if present
            if item.get("strategic_learning"):
                response += f"   **Strategic**: {item['strategic_learning'][:200]}...\n"

            # Include meta-learning if present
            if item.get("meta_learning"):
                response += f"   **Meta-Learning**: {item['meta_learning'][:200]}...\n"

            # Include anti-patterns if present
            if item.get("anti_patterns"):
                anti_patterns = item["anti_patterns"]
                if isinstance(anti_patterns, dict) and anti_patterns.get("description"):
                    response += f"   **Anti-Patterns**: {anti_patterns['description'][:200]}...\n"
                elif isinstance(anti_patterns, list) and anti_patterns:
                    response += f"   **Anti-Patterns**: {len(anti_patterns)} found\n"

            # Include execution metadata insights if high confidence
            if item.get("confidence_score", 0) > 0.7:
                response += f"   **Confidence**: {item['confidence_score']:.1%} ✅\n"
            elif item.get("confidence_score"):
                response += f"   **Confidence**: {item['confidence_score']:.1%}\n"

            # Show execution efficiency if available
            exec_meta = item.get("execution_metadata", {})
            if exec_meta.get("efficiency_score") is not None:
                score = exec_meta["efficiency_score"]
                response += f"   **Efficiency**: {score:.1%}"
                if score < 0.5:
                    response += " ⚠️ (improvements needed)"
                response += "\n"
    else:
        response += "No similar past tasks found.\n"

    if applicable_patterns:
        response += "\n**High-Confidence Patterns:**\n"
        for pattern in applicable_patterns[:3]:
            response += f"• {pattern}\n"

    # Store comprehensive learnings in state for agent to use
    relevant_learnings = []
    for item in similar_task_learnings[:3]:
        learning_summary = f"{item['similar_task']}: "

        # Prioritize strategic and tactical learnings
        if item.get("strategic_learning"):
            learning_summary += item["strategic_learning"][:100]
        elif item.get("tactical_learning"):
            learning_summary += item["tactical_learning"][:100]
        else:
            learning_summary += item.get("learning", "No specific learning")[:100]

        relevant_learnings.append(learning_summary)

    return Command(
        update={
            "relevant_learnings": relevant_learnings,
            "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
        }
    )


@tool
async def queue_learning(
    task: str,
    outcome: str,
    description: str,
    state: Annotated[LearningAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    duration: float = 0.0,
    context: str | None = None,
    error: str | None = None,
) -> Command[Any]:
    """Queue a task execution for explicit pattern extraction and learning.

    Note: Routine conversation learning happens automatically after each interaction.
    Use this tool only when you want to explicitly capture a specific pattern or insight.

    Args:
        task: The task that was executed
        outcome: 'success' or 'failure'
        description: Description of what happened
        duration: How long the task took
        context: Additional context about the execution
        error: Error message if the task failed
    """
    # Import here to avoid circular imports
    from learning_agent.learning.langmem_integration import get_learning_system

    # Create execution data for learning
    execution_data = ExecutionData(
        task=task,
        context=context,
        outcome=outcome,  # type: ignore
        duration=duration,
        description=description,
        error=error,
    )

    # Get existing queue and update state
    current_queue = state.get("learning_queue", [])
    updated_queue = [*current_queue, execution_data]

    # Submit to LangMem ReflectionExecutor for immediate processing
    # No delay needed since the task is already complete
    learning_system = get_learning_system()
    await learning_system.submit_task_execution_for_learning(
        task=task,
        outcome=outcome,
        description=description,
        context=context,
        error=error,
        duration=duration,
        delay_seconds=0,  # Process immediately since task is complete
    )

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


# Note: apply_pattern, create_memory, and create_pattern have been removed
# All memory and pattern storage is now handled automatically through PostgreSQL
# The agent doesn't need manual memory/pattern creation tools


def create_learning_tools() -> list[BaseTool]:
    """Create all learning-specific tools for the deepagents agent."""
    return [
        search_memory,
        queue_learning,
    ]
