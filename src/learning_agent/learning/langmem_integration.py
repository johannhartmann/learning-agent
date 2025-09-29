"""LangMem integration for memory processing with PostgreSQL vector storage."""

import asyncio
import contextvars
import logging
import os
from copy import deepcopy
from typing import Any

import httpx
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from learning_agent.config import settings
from learning_agent.learning.vector_storage import VectorLearningStorage
from learning_agent.providers import get_chat_model


def compute_learning_relevance_signals(
    messages: list[BaseMessage],
    metadata: dict[str, Any] | None,
    execution_analysis: dict[str, Any] | None,
) -> list[str]:
    """Determine whether a conversation produced learnings worth persisting."""

    metadata = metadata or {}
    execution_analysis = execution_analysis or {}

    signals: list[str] = []

    # Evidence that the agent touched tools / environment
    total_tool_calls = execution_analysis.get("total_tool_calls")
    if isinstance(total_tool_calls, int | float) and total_tool_calls > 0:
        signals.append("tool_usage")

    if execution_analysis.get("inefficiencies") or execution_analysis.get("redundancies"):
        signals.append("analysis_findings")

    if any(getattr(msg, "type", "") == "tool" for msg in messages):
        signals.append("tool_messages")

    # Evidence of task progress or explicit execution metadata
    completed_count = metadata.get("completed_count")
    if isinstance(completed_count, int) and completed_count > 0:
        signals.append("completed_tasks")

    todos = metadata.get("todos")
    if isinstance(todos, list) and any(
        isinstance(todo, dict)
        and str(todo.get("status", "")).lower() not in {"", "pending", "todo", "not_started"}
        for todo in todos
    ):
        signals.append("todo_progress")

    if metadata.get("type") == "task_execution":
        signals.append("task_execution_event")

    outcome = metadata.get("outcome")
    if isinstance(outcome, str) and outcome.lower() == "failure":
        signals.append("failure_outcome")

    if metadata.get("has_error"):
        signals.append("execution_error")

    if metadata.get("error"):
        signals.append("reported_error")

    # Deduplicate while preserving order
    return list(dict.fromkeys(signals))


class AntiPatterns(BaseModel):
    """Anti-patterns and inefficiencies discovered."""

    description: str = Field(description="General description of what NOT to do")
    redundancies: list[str] = Field(
        default_factory=list, description="List of redundant operations found"
    )
    inefficiencies: list[str] = Field(
        default_factory=list, description="List of inefficient approaches discovered"
    )


class LearningExtraction(BaseModel):
    """Structured learning extraction from task execution."""

    tactical_learning: str = Field(
        description="Specific implementation insights: What specific implementation approach worked or didn't work? Which tools were most effective? What code patterns or techniques were discovered?"
    )
    strategic_learning: str = Field(
        description="Higher-level patterns: What general approach or strategy emerged? How should similar problems be approached in the future? What architectural or design patterns apply?"
    )
    meta_learning: str = Field(
        description="Learning about learning: How effective was the search for past experiences? What about the learning process itself could be improved? Were past learnings applied effectively?"
    )
    anti_patterns: AntiPatterns = Field(
        description="What NOT to do: inefficiencies, redundancies, and approaches to avoid"
    )
    confidence_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in these learnings (0.0-1.0)"
    )


class LangMemLearningSystem:
    """Learning system that processes memories and stores them with vector embeddings."""

    def __init__(self, database_url: str | None = None):
        """Initialize the LangMem learning system."""
        # Initialize LLM for processing
        self.llm = get_chat_model(settings)

        # Create structured LLM for learning extraction
        self.structured_llm = self.llm.with_structured_output(LearningExtraction)

        # Initialize vector storage for learnings
        self.storage = VectorLearningStorage(database_url)

        # Background reflection handling
        self._background_delay = float(os.getenv("LEARNING_BACKGROUND_DELAY", "30"))
        self._background_lock = asyncio.Lock()
        self._background_task: asyncio.Task[None] | None = None
        self._pending_payload: dict[str, Any] | None = None
        self._logger = logging.getLogger(__name__)

    async def _process_and_store_memory(
        self, messages: list[BaseMessage], metadata: dict[str, Any]
    ) -> None:
        """Process messages with deep reflection to extract multi-dimensional learnings."""
        try:
            # Convert messages to a narrative format for processing
            narrative_parts = []
            for msg in messages:
                role = msg.__class__.__name__.replace("Message", "")
                content = str(msg.content)
                narrative_parts.append(f"{role}: {content}")

            full_narrative = "\n".join(narrative_parts)

            # Analyze execution trace for inefficiencies
            from learning_agent.learning.execution_analyzer import ExecutionAnalyzer

            analyzer = ExecutionAnalyzer()
            execution_analysis = analyzer.analyze_conversation(
                [{"content": part} for part in narrative_parts]
            )

            relevance_signals = compute_learning_relevance_signals(
                messages=messages,
                metadata=metadata,
                execution_analysis=execution_analysis,
            )

            if not relevance_signals:
                self._logger.info(
                    "Skipping deep learning storage: no relevance signals detected",
                )
                return

            # Use structured LLM for deep multi-dimensional reflection
            extraction_prompt = f"""Perform a DEEP REFLECTION on this task execution to extract insightful learnings.

CONVERSATION:
{full_narrative}

EXECUTION ANALYSIS:
- Tool usage pattern: {execution_analysis.get("execution_patterns", {}).get("workflow_pattern", "unknown")}
- Efficiency score: {execution_analysis.get("efficiency_score", 0):.2f}
- Redundancies found: {len(execution_analysis.get("redundancies", []))}
- Inefficiencies found: {len(execution_analysis.get("inefficiencies", []))}
- Parallelization opportunities: {len(execution_analysis.get("parallelization_opportunities", []))}

Redundancy details: {execution_analysis.get("redundancies", [])}
Inefficiency details: {execution_analysis.get("inefficiencies", [])}

Extract learnings from this task execution with specific, actionable insights."""

            # Get structured learning extraction
            learning_result = await self.structured_llm.ainvoke(
                [HumanMessage(content=extraction_prompt)]
            )

            if learning_result and isinstance(learning_result, LearningExtraction):
                from datetime import datetime
                from uuid import uuid4

                metadata.setdefault("learning_signals", relevance_signals)

                # Merge execution analysis items (dicts) with LLM-extracted (strings)
                def _stringify_items(items: list[Any]) -> list[str]:
                    out: list[str] = []
                    for it in items:
                        if isinstance(it, dict):
                            # Prefer suggestion or type for a stable string
                            s = (
                                str(it.get("suggestion"))
                                if "suggestion" in it
                                else f"{it.get('type', 'item')}: {it}"
                            )
                            out.append(s)
                        else:
                            out.append(str(it))
                    return out

                red_exec = _stringify_items(execution_analysis.get("redundancies", []))
                ineff_exec = _stringify_items(execution_analysis.get("inefficiencies", []))

                # Deduplicate by string value to avoid unhashable dicts
                all_redundancies = sorted(
                    set(red_exec + list(learning_result.anti_patterns.redundancies))
                )
                all_inefficiencies = sorted(
                    set(ineff_exec + list(learning_result.anti_patterns.inefficiencies))
                )

                # Store the deep learning memory using structured data
                memory = {
                    "id": str(uuid4()),
                    "task": metadata.get("task", "Conversation"),
                    "context": full_narrative[:500],
                    "narrative": full_narrative,
                    "reflection": f"Tactical: {learning_result.tactical_learning}\n\nStrategic: {learning_result.strategic_learning}\n\nMeta: {learning_result.meta_learning}",
                    "tactical_learning": learning_result.tactical_learning,
                    "strategic_learning": learning_result.strategic_learning,
                    "meta_learning": learning_result.meta_learning,
                    "anti_patterns": {
                        "description": learning_result.anti_patterns.description,
                        "redundancies": all_redundancies,
                        "inefficiencies": all_inefficiencies,
                    },
                    "execution_metadata": {
                        "tool_counts": execution_analysis.get("tool_counts", {}),
                        "efficiency_score": execution_analysis.get("efficiency_score", 0),
                        "patterns": execution_analysis.get("execution_patterns", {}),
                        "parallelization_opportunities": execution_analysis.get(
                            "parallelization_opportunities", []
                        ),
                    },
                    "confidence_score": learning_result.confidence_score,
                    "outcome": metadata.get("outcome", "success"),
                    "timestamp": datetime.now(),
                    "metadata": metadata,
                }

                memory_id = await self.storage.store_memory(memory)
                memory["id"] = memory_id  # Update with actual stored ID

                # Update thread state with new memory for UI display
                thread_id = metadata.get("thread_id")
                if thread_id:
                    await self._update_thread_state(thread_id, memory)

                # Log for debugging
                self._logger.info(
                    f"Stored deep learning memory: {memory_id} - {memory['task']} "
                    f"(confidence: {learning_result.confidence_score:.2f})"
                )

        except Exception:
            self._logger.exception("Error processing and storing deep learning memory")

    async def _update_thread_state(self, thread_id: str, memory: dict[str, Any]) -> None:
        """Update the thread state with new memory for UI display.

        This allows the UI to show learning results from the current session
        without blocking the graph execution.
        """
        try:
            # Get LangGraph server URL
            langgraph_url = os.environ.get(
                "LANGGRAPH_SERVER_URL",
                "http://localhost:2024"
                if os.environ.get("ENV") == "local"
                else "http://server:2024",
            )

            # Prepare simplified memory for UI display
            timestamp_val = memory.get("timestamp")
            ui_memory = {
                "id": memory.get("id"),
                "task": memory.get("task"),
                "tactical_learning": memory.get("tactical_learning"),
                "strategic_learning": memory.get("strategic_learning"),
                "meta_learning": memory.get("meta_learning"),
                "confidence_score": memory.get("confidence_score"),
                "timestamp": timestamp_val.isoformat() if timestamp_val else None,
            }

            # Make HTTP PATCH request to update thread state
            # First, get the current state to append to existing memories
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:  # nosec B113
                # Get current state
                get_response = await client.get(
                    f"{langgraph_url}/threads/{thread_id}/state",
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-Key": "test-key",
                    },
                    timeout=5.0,
                )

                existing_memories = []
                if get_response.status_code == 200:
                    current_state = get_response.json()
                    existing_memories = current_state.get("values", {}).get("memories", [])

                # Append new memory to existing ones
                updated_memories = [*existing_memories, ui_memory]

                # Update state with appended memories
                response = await client.patch(
                    f"{langgraph_url}/threads/{thread_id}/state",
                    json={
                        "values": {
                            "memories": updated_memories,
                        },
                        "as_node": "learning_update",  # Identify the update source
                    },
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-Key": "test-key",  # Use appropriate API key
                    },
                    timeout=5.0,
                )

                if response.status_code == 200:
                    self._logger.info(
                        f"Successfully updated thread state with memory for thread {thread_id}"
                    )
                else:
                    self._logger.warning(
                        f"Failed to update thread state: {response.status_code} - {response.text}"
                    )

        except Exception:
            # Don't let state update failures break the learning process
            self._logger.exception(f"Error updating thread state for {thread_id}")

    async def _schedule_processing(
        self,
        messages: list[BaseMessage],
        metadata: dict[str, Any],
    ) -> None:
        """Schedule background processing with debounce semantics."""

        # Ensure we keep a snapshot of payload to avoid mutation downstream
        payload = {
            "messages": deepcopy(messages),
            "metadata": deepcopy(metadata),
        }

        async with self._background_lock:
            if self._background_task and not self._background_task.done():
                self._background_task.cancel()
                try:
                    await self._background_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    self._logger.exception("Background learning task error during cancellation")

            self._pending_payload = payload
            empty_context = contextvars.Context()
            self._background_task = asyncio.create_task(
                self._delayed_process(),
                context=empty_context,
            )

    async def _delayed_process(self) -> None:
        try:
            await asyncio.sleep(max(self._background_delay, 0))
            async with self._background_lock:
                payload = self._pending_payload
                self._pending_payload = None

            if not payload:
                return

            await self._process_and_store_memory(payload["messages"], payload["metadata"])
        except asyncio.CancelledError:
            raise
        except Exception:
            self._logger.exception("Background learning task failed")

    async def submit_conversation_for_learning(
        self,
        messages: list[BaseMessage],
        delay_seconds: int = 0,  # noqa: ARG002
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Submit conversation data for memory processing.

        Args:
            messages: Conversation messages to process
            delay_seconds: Delay before processing (kept for API compatibility)
            metadata: Additional metadata about the conversation
        """
        await self._schedule_processing(messages, metadata or {})

    async def submit_task_execution_for_learning(
        self,
        task: str,
        outcome: str,
        description: str,
        context: str | None = None,
        error: str | None = None,
        duration: float = 0.0,
        delay_seconds: int = 0,  # noqa: ARG002
    ) -> None:
        """Submit task execution data for learning.

        Args:
            task: The task that was executed
            outcome: 'success' or 'failure'
            description: Description of what happened
            context: Additional context
            error: Error message if failed
            duration: Execution duration
            delay_seconds: Delay before processing (kept for API compatibility)
        """
        # Convert execution data to messages for memory processing
        messages: list[BaseMessage] = []

        # Create narrative from task data
        narrative = f"Task: {task}\n"
        if context:
            narrative += f"Context: {context}\n"
        narrative += f"Description: {description}\n"
        narrative += f"Outcome: {outcome}\n"
        if error:
            narrative += f"Error: {error}\n"
        if duration > 0:
            narrative += f"Duration: {duration:.2f}s\n"

        messages.append(HumanMessage(content=narrative))

        learning_signals: list[str] = []
        if outcome == "failure":
            learning_signals.append("failure_outcome")
        if error:
            learning_signals.append("execution_error")
        if duration > 0:
            learning_signals.append("analysis_findings")

        metadata = {
            "type": "task_execution",
            "task": task,
            "outcome": outcome,
            "duration": duration,
            "has_error": error is not None,
            "learning_signals": learning_signals,
        }

        await self._schedule_processing(messages, metadata)

    async def get_recent_memories(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recently processed memories from storage."""
        return await self.storage.get_recent_memories(limit)

    async def search_memories(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search memories using vector similarity."""
        return await self.storage.search_similar_memories(query, limit)

    async def search_similar_tasks(self, current_task: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for similar tasks and return their learnings."""
        return await self.storage.search_similar_tasks(current_task, limit)

    async def get_processed_memories_for_ui(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Get processed memories, patterns, and learning queue for UI display.

        Returns:
            Tuple of (memories, patterns, learning_queue)
        """
        # Initialize storage if needed
        if not self.storage.pool:
            await self.storage.initialize()

        # Get recent memories from vector storage
        memories = await self.get_recent_memories(limit=20)

        # Convert to UI format
        ui_memories: list[dict[str, Any]] = []
        for memory in memories:
            if isinstance(memory, dict):
                ui_memories.append(
                    {
                        "id": memory.get("id", str(len(ui_memories))),
                        "task": memory.get("task", "Unknown task"),
                        "context": memory.get("context"),
                        "narrative": memory.get("narrative", ""),
                        "reflection": memory.get("reflection", ""),
                        "tactical_learning": memory.get("tactical_learning"),
                        "strategic_learning": memory.get("strategic_learning"),
                        "meta_learning": memory.get("meta_learning"),
                        "anti_patterns": memory.get("anti_patterns"),
                        "execution_metadata": memory.get("execution_metadata"),
                        "confidence_score": memory.get("confidence_score", 0.5),
                        "outcome": memory.get("outcome", "success"),
                        "timestamp": memory.get("timestamp", ""),
                        "embedding": None,  # Don't send raw embeddings to UI
                        "similarity": memory.get("similarity"),  # Include similarity if present
                    }
                )

        # Get patterns and queue from storage
        patterns = await self.storage.get_patterns(limit=20)
        learning_queue = await self.storage.get_learning_queue(limit=20)

        return ui_memories, patterns, learning_queue

    async def close(self) -> None:
        """Close database connections."""
        async with self._background_lock:
            if self._background_task and not self._background_task.done():
                self._background_task.cancel()
                try:
                    await self._background_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    self._logger.exception("Error while cancelling background learning task")
            self._background_task = None
            self._pending_payload = None

        await self.storage.close()


# Global instance for the learning system
_learning_system: LangMemLearningSystem | None = None


def get_learning_system(database_url: str | None = None) -> LangMemLearningSystem:
    """Get or create the global learning system instance."""
    global _learning_system
    if _learning_system is None:
        db_url = database_url or os.getenv("DATABASE_URL")
        _learning_system = LangMemLearningSystem(db_url)
    return _learning_system


def initialize_learning_system(database_url: str | None = None) -> LangMemLearningSystem:
    """Initialize the learning system."""
    global _learning_system
    db_url = database_url or os.getenv("DATABASE_URL")
    _learning_system = LangMemLearningSystem(db_url)
    return _learning_system
