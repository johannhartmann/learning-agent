"""Learning supervisor that integrates deepagents with background learning."""

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from learning_agent.agent import create_learning_agent
from learning_agent.learning.narrative_learner import NarrativeLearner


class LearningSupervisor:
    """
    Supervisor that wraps deepagents with background learning capabilities.

    This class bridges the gap between the deepagents-based execution system
    and the langmem-based learning system, providing:
    - Task execution via deepagents
    - Background learning via NarrativeLearner
    - State persistence and retrieval
    """

    def __init__(self, storage_path: Path | None = None, model: str | None = None):
        """Initialize the learning supervisor.

        Args:
            storage_path: Path for learning storage (defaults to .agent/)
            model: Model name to use (defaults to config setting)
        """
        self.storage_path = storage_path or Path(".agent")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Create the deepagents-based agent
        self.agent = create_learning_agent(storage_path=self.storage_path, model=model)

        # Create the narrative learner for background learning
        self.narrative_learner = NarrativeLearner(storage_path=self.storage_path / "narratives")

        # Track state
        self._background_started = False
        self.current_thread_id: str | None = None

    async def process_task(
        self,
        task: str,
        context: str | None = None,
        progress_callback: Any = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Process a task through the learning agent.

        Args:
            task: The task to accomplish
            context: Additional context about the environment
            progress_callback: Optional callback for progress updates (unused)

        Returns:
            Execution result with learning integration
        """
        # Start background processor on first use
        if not self._background_started:
            await self.narrative_learner.start_background_processor()
            self._background_started = True

        # Create thread ID for this execution
        self.current_thread_id = str(uuid4())
        start_time = datetime.now()

        try:
            # First, search for relevant memories to populate state
            quick_context = await self.narrative_learner.get_quick_context(task)

            # Create initial state with learning context
            initial_state = {
                "messages": [{"role": "user", "content": task}],
                "todos": [],
                "files": {},
                "memories": [],
                "patterns": [],
                "current_context": {
                    "task": task,
                    "context": context,
                    "thread_id": self.current_thread_id,
                    "start_time": start_time.isoformat(),
                },
                "learning_queue": [],
                "relevant_memories": quick_context.get("recent_memories", [])[:3],
                "applicable_patterns": [],
            }

            # Execute through deepagents
            result = await self.agent.ainvoke(initial_state)  # type: ignore[attr-defined]

            # Extract execution data for learning
            execution_duration = (datetime.now() - start_time).total_seconds()

            # Determine outcome based on result
            outcome = "success"
            error_msg = None
            description = "Task completed successfully"

            if "error" in str(result).lower() or "failed" in str(result).lower():
                outcome = "failure"
                error_msg = str(result)
                description = f"Task failed: {error_msg}"
            else:
                # Extract meaningful description from result
                if result.get("messages"):
                    last_message = result["messages"][-1]
                    if hasattr(last_message, "content"):
                        description = last_message.content[:500]

            # Schedule background learning
            self.narrative_learner.schedule_post_execution_learning(
                {
                    "task": task,
                    "context": context,
                    "outcome": outcome,
                    "duration": execution_duration,
                    "description": description,
                    "error": error_msg,
                }
            )

        except Exception as e:
            # Handle execution errors
            execution_duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)

            # Still queue learning from failure
            self.narrative_learner.schedule_post_execution_learning(
                {
                    "task": task,
                    "context": context,
                    "outcome": "failure",
                    "duration": execution_duration,
                    "description": f"Execution error: {error_msg}",
                    "error": error_msg,
                }
            )

            return {
                "status": "error",
                "task": task,
                "duration": execution_duration,
                "error": error_msg,
                "summary": f"Task failed with error: {error_msg}",
                "thread_id": self.current_thread_id,
                "learning_queued": True,
            }
        else:
            # Return formatted result for successful execution
            return {
                "status": "completed" if outcome == "success" else "failed",
                "task": task,
                "duration": execution_duration,
                "result": result,
                "summary": description,
                "thread_id": self.current_thread_id,
                "learning_queued": True,
            }

    async def resume_task(self, thread_id: str) -> dict[str, Any]:
        """Resume a task from a checkpoint.

        Note: This is a simplified implementation. Full checkpoint/resume
        would require deeper integration with deepagents' state management.

        Args:
            thread_id: The thread ID to resume from

        Returns:
            Execution result
        """
        # For now, return a not implemented response
        # Full implementation would require deepagents checkpoint integration
        return {
            "status": "error",
            "error": f"Resume not yet implemented for thread {thread_id}",
            "thread_id": thread_id,
        }

    async def get_learning_stats(self) -> dict[str, Any]:
        """Get statistics about the learning system.

        Returns:
            Learning system statistics
        """
        # This would integrate with NarrativeLearner's stats
        return {
            "memories_count": 0,  # Would query actual memory store
            "patterns_count": 0,  # Would query actual pattern store
            "background_processor_active": self._background_started,
            "storage_path": str(self.storage_path),
        }

    async def shutdown(self) -> None:
        """Shutdown the supervisor and background learning."""
        if self._background_started:
            await self.narrative_learner.stop_background_processor()
            self._background_started = False
