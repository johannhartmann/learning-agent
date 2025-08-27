"""Integration tests for the Learning Agent system."""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from learning_agent.agent import create_learning_agent
from learning_agent.learning.narrative_learner import NarrativeLearner
from learning_agent.learning_supervisor import LearningSupervisor
from learning_agent.state import ExecutionData, LearningAgentState


# Test data classes
@dataclass
class Memory:
    """Test memory class."""

    id: str
    task: str
    context: str
    narrative: str
    reflection: str
    outcome: str
    timestamp: str


@dataclass
class Pattern:
    """Test pattern class."""

    id: str
    description: str
    confidence: float
    success_rate: float
    applications: int


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestNarrativeLearner:
    """Test narrative learner functionality."""

    @pytest.mark.asyncio
    async def test_get_quick_context(self, temp_storage):
        """Test getting quick context for a task."""
        learner = NarrativeLearner(storage_path=temp_storage)

        # Get quick context should always work even with no memories
        context = await learner.get_quick_context("Test task")

        assert isinstance(context, dict)
        assert "has_prior_experience" in context
        assert "recent_memories" in context
        assert isinstance(context["recent_memories"], list)

    @pytest.mark.asyncio
    async def test_schedule_learning(self, temp_storage):
        """Test scheduling post-execution learning."""
        learner = NarrativeLearner(storage_path=temp_storage)

        # Start the background processor first
        await learner.start_background_processor()

        execution_data = {
            "task": "Test task",
            "context": None,
            "outcome": "success",
            "duration": 1.5,
            "description": "Test completed successfully",
            "error": None,
        }

        # This should not raise an exception
        learner.schedule_post_execution_learning(execution_data)

        # Give it a moment to process
        import asyncio

        await asyncio.sleep(0.1)

        # Verify the background processor is running
        assert learner.background_task is not None

        # Clean up
        await learner.stop_background_processor()


class TestLearningSupervisor:
    """Test the learning supervisor."""

    @pytest.mark.asyncio
    async def test_process_simple_task(self, temp_storage):
        """Test processing a simple task."""
        supervisor = LearningSupervisor(storage_path=temp_storage)

        result = await supervisor.process_task("Say hello")

        assert result is not None
        assert "status" in result
        assert "duration" in result
        assert "thread_id" in result
        assert "learning_queued" in result

        await supervisor.shutdown()

    @pytest.mark.asyncio
    async def test_process_with_context(self, temp_storage):
        """Test processing with context."""
        supervisor = LearningSupervisor(storage_path=temp_storage)

        result = await supervisor.process_task("Count to 3", context="This is a test")

        assert result is not None
        assert result["task"] == "Count to 3"
        assert "summary" in result

        await supervisor.shutdown()

    @pytest.mark.asyncio
    async def test_learning_stats(self, temp_storage):
        """Test getting learning statistics."""
        supervisor = LearningSupervisor(storage_path=temp_storage)

        stats = await supervisor.get_learning_stats()

        assert stats is not None
        assert "memories_count" in stats
        assert "patterns_count" in stats
        assert "background_processor_active" in stats

        await supervisor.shutdown()


class TestDeepAgentsIntegration:
    """Test deepagents integration."""

    def test_create_agent(self, temp_storage):
        """Test creating a deepagents-based agent."""
        agent = create_learning_agent(storage_path=temp_storage)
        assert agent is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
    async def test_agent_invocation(self, temp_storage):
        """Test invoking the agent with state."""
        agent = create_learning_agent(storage_path=temp_storage)

        initial_state: LearningAgentState = {
            "messages": [{"role": "user", "content": "Say hello"}],
            "todos": [],
            "files": {},
            "memories": [],
            "patterns": [],
            "learning_queue": [],
            "relevant_memories": [],
            "applicable_patterns": [],
        }

        result = await agent.ainvoke(initial_state)

        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1


class TestLearningState:
    """Test learning state components."""

    def test_memory_creation(self):
        """Test creating a memory."""
        from datetime import datetime
        from uuid import uuid4

        memory = Memory(
            id=str(uuid4()),
            task="Test task",
            context="Test context",
            narrative="Test narrative",
            reflection="Test reflection",
            outcome="success",
            timestamp=datetime.now().isoformat(),
        )

        assert memory.task == "Test task"
        assert memory.outcome == "success"
        assert memory.context == "Test context"

    def test_pattern_creation(self):
        """Test creating a pattern."""
        from uuid import uuid4

        pattern = Pattern(
            id=str(uuid4()),
            description="Test pattern",
            confidence=0.8,
            success_rate=0.9,
            applications=3,
        )

        assert pattern.confidence == 0.8
        assert pattern.success_rate == 0.9
        assert pattern.applications == 3

    def test_execution_data(self):
        """Test execution data."""
        exec_data = ExecutionData(
            task="Test task",
            context="Test context",
            outcome="failure",
            duration=3.5,
            description="Test failed",
            error="Test error",
        )

        assert exec_data.task == "Test task"
        assert exec_data.outcome == "failure"
        assert exec_data.error == "Test error"
