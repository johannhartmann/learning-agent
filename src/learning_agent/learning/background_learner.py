"""Background learning system using LangMem for postponed/async learning."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langmem import create_memory_manager

from learning_agent.config import settings
from learning_agent.providers import get_chat_model


class BackgroundLearner:
    """
    Handles background learning and memory management using LangMem.

    This allows tasks to execute quickly while learning happens asynchronously.
    """

    def __init__(self, storage_path: Path | None = None):
        """Initialize the background learner."""
        self.storage_path = storage_path or Path(".agent") / "langmem"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize LLM
        self.llm = get_chat_model(settings)

        # Initialize memory manager using langmem
        # First argument is positional-only
        self.memory_manager = create_memory_manager(
            self.llm,  # positional-only argument
            enable_inserts=True,
            enable_updates=True,
            enable_deletes=False,
        )

        # Queue for postponed learning tasks
        self.learning_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self.background_task: asyncio.Task[None] | None = None

        # Quick access cache for recent memories
        self.recent_cache: list[dict[str, Any]] = []
        self.max_cache_size = 10

    async def start_background_processor(self) -> None:
        """Start the background learning processor."""
        if self.background_task is None or self.background_task.done():
            self.background_task = asyncio.create_task(self._process_learning_queue())

    async def stop_background_processor(self) -> None:
        """Stop the background processor gracefully."""
        if self.background_task and not self.background_task.done():
            # Signal to stop by putting None
            await self.learning_queue.put(None)
            await self.background_task

    async def _process_learning_queue(self) -> None:
        """Process learning tasks in the background."""
        while True:
            try:
                # Get next learning task
                task = await self.learning_queue.get()

                if task is None:  # Shutdown signal
                    break

                # Process the learning task
                await self._process_learning_task(task)

            except Exception as e:
                print(f"Background learning error: {e}")
                # Continue processing other tasks

    async def _process_learning_task(self, task: dict[str, Any]) -> None:
        """Process a single learning task."""
        task_type = task.get("type")

        if task_type == "reflection":
            await self._background_reflect(task)
        elif task_type == "consolidation":
            await self._background_consolidate(task)
        elif task_type == "episode_storage":
            await self._background_store_episode(task)

    async def _background_reflect(self, task: dict[str, Any]) -> None:
        """Perform reflection in background using langmem."""
        execution_data = task.get("execution_data", {})

        # Convert execution data to messages for langmem
        messages = [
            SystemMessage(content=f"Task: {execution_data.get('task', 'Unknown')}"),
            HumanMessage(content=f"Process: {execution_data.get('process', '')}"),
            SystemMessage(content=f"Outcome: {execution_data.get('outcome', {})}"),
        ]

        try:
            # Extract memories using langmem
            memories = await self.memory_manager.ainvoke(
                {
                    "messages": messages,
                    "existing": self.recent_cache[-5:] if self.recent_cache else [],
                }
            )

            # Update cache with new memories
            for memory in memories:
                self._update_cache(
                    {
                        "type": "reflection",
                        "content": str(memory),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        except Exception as e:
            print(f"Reflection error: {e}")

    async def _background_consolidate(self, task: dict[str, Any]) -> None:  # noqa: ARG002
        """Consolidate memories in background."""
        # For now, just keep the cache updated
        # Real consolidation would merge and compress memories
        if len(self.recent_cache) > self.max_cache_size:
            # Keep only the most recent memories
            self.recent_cache = self.recent_cache[-self.max_cache_size :]

    async def _background_store_episode(self, task: dict[str, Any]) -> None:
        """Store episode in background."""
        episode_data = task.get("episode_data", {})

        # Create episode memory
        episode_memory = {
            "content": f"Task: {episode_data.get('task')}\nOutcome: {episode_data.get('outcome')}",
            "type": "episode",
            "timestamp": datetime.now().isoformat(),
            "metadata": episode_data,
        }

        # Store in cache
        self._update_cache(episode_memory)

    def _update_cache(self, entry: dict[str, Any]) -> None:
        """Update the recent cache."""
        self.recent_cache.append(entry)
        if len(self.recent_cache) > self.max_cache_size:
            self.recent_cache.pop(0)

    async def queue_for_learning(self, task_type: str, data: dict[str, Any]) -> None:
        """
        Queue a task for background learning.

        This returns immediately, allowing the main execution to continue.
        """
        learning_task = {
            "id": str(uuid4()),
            "type": task_type,
            "timestamp": datetime.now().isoformat(),
            **data,
        }

        await self.learning_queue.put(learning_task)

    async def get_relevant_memories(self, query: str, k: int = 5) -> list[dict[str, Any]]:  # noqa: ARG002
        """
        Get relevant memories for a query.

        This is fast as it queries existing memories without processing.
        """
        # For now, just return from cache
        if self.recent_cache:
            # Return recent memories if available
            return self.recent_cache[-k:]

        return []

    async def get_quick_context(self, task: str) -> dict[str, Any]:
        """
        Get quick context for a task without blocking.

        Returns immediately with available information.
        """
        # Check if we have recent relevant memories
        relevant = await self.get_relevant_memories(task, k=3)

        return {
            "has_prior_experience": len(relevant) > 0,
            "recent_memories": relevant,
            "confidence": 0.5 if relevant else 0.1,  # Lower confidence without full analysis
        }

    def schedule_post_execution_learning(self, execution_data: dict[str, Any]) -> None:
        """
        Schedule learning after task execution.

        This is fire-and-forget - returns immediately.
        """
        # Queue reflection task
        task1 = asyncio.create_task(
            self.queue_for_learning("reflection", {"execution_data": execution_data})
        )
        # Store reference to prevent task from being garbage collected
        task1.add_done_callback(lambda _: None)

        # Queue episode storage
        task2 = asyncio.create_task(
            self.queue_for_learning(
                "episode_storage",
                {
                    "episode_data": {
                        "task": execution_data.get("task"),
                        "description": execution_data.get("description", ""),
                        "outcome": execution_data.get("outcome"),
                        "duration": execution_data.get("duration"),
                    }
                },
            )
        )
        # Store reference to prevent task from being garbage collected
        task2.add_done_callback(lambda _: None)

        # Schedule consolidation after some delay
        task3 = asyncio.create_task(self._delayed_consolidation())
        # Store reference to prevent task from being garbage collected
        task3.add_done_callback(lambda _: None)

    async def _delayed_consolidation(self) -> None:
        """Schedule consolidation after a delay."""
        await asyncio.sleep(30)  # Wait 30 seconds before consolidating
        await self.queue_for_learning("consolidation", {})
