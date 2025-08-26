"""LangMem integration for memory processing with PostgreSQL vector storage."""

import os
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from learning_agent.config import settings
from learning_agent.learning.vector_storage import VectorLearningStorage
from learning_agent.providers import get_chat_model


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

            if learning_result:
                from datetime import datetime
                from uuid import uuid4

                # Merge execution analysis redundancies with LLM-extracted ones
                all_redundancies = list(
                    set(
                        execution_analysis.get("redundancies", [])
                        + learning_result.anti_patterns.redundancies
                    )
                )

                all_inefficiencies = list(
                    set(
                        execution_analysis.get("inefficiencies", [])
                        + learning_result.anti_patterns.inefficiencies
                    )
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

                # Log for debugging
                import logging

                logger = logging.getLogger(__name__)
                logger.info(
                    f"Stored deep learning memory: {memory_id} - {memory['task']} "
                    f"(confidence: {learning_result.confidence_score:.2f})"
                )

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Error processing and storing deep learning memory")

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
        # Process immediately and await completion
        await self._process_and_store_memory(messages, metadata or {})

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

        # Create metadata
        metadata = {
            "type": "task_execution",
            "task": task,
            "outcome": outcome,
            "duration": duration,
            "has_error": error is not None,
        }

        # Submit for processing
        await self._process_and_store_memory(messages, metadata)

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
