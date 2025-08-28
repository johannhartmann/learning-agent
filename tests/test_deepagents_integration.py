"""Integration tests for the deepagents-based Learning Agent."""

import asyncio
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from learning_agent.agent import create_learning_agent
from learning_agent.learning.narrative_learner import NarrativeLearner
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


class TestLearningAgent:
    """Test the deepagents-based learning agent."""

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
    def test_create_agent(self):
        """Test creating a learning agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_learning_agent(storage_path=Path(tmpdir))
            assert agent is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
    async def test_agent_with_state(self):
        """Test agent invocation with custom state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_learning_agent(storage_path=Path(tmpdir))

            # Create initial state
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

            # Invoke agent
            result = await agent.ainvoke(initial_state)

            assert result is not None
            assert "messages" in result
            assert len(result["messages"]) > 1  # Should have response


class TestNarrativeLearner:
    """Test the narrative learner with deepagents integration."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
    async def test_narrative_learner_quick_context(self):
        """Test getting quick context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = NarrativeLearner(storage_path=Path(tmpdir))

            # Get quick context for a task
            context = await learner.get_quick_context("Write a function")

            assert context is not None
            assert "has_prior_experience" in context
            assert "recent_memories" in context
            assert isinstance(context["recent_memories"], list)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
    async def test_narrative_learner_background_processing(self):
        """Test background learning processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learner = NarrativeLearner(storage_path=Path(tmpdir))

            # Start background processor
            await learner.start_background_processor()

            # Schedule learning
            execution_data = {
                "task": "Test task",
                "context": None,
                "outcome": "success",
                "duration": 1.0,
                "description": "Test completed",
                "error": None,
            }

            learner.schedule_post_execution_learning(execution_data)

            # Give it time to process
            await asyncio.sleep(0.5)

            # Stop background processor
            await learner.stop_background_processor()


class TestLearningState:
    """Test the learning agent state."""

    def test_memory_creation(self):
        """Test creating a memory."""
        from datetime import datetime
        from uuid import uuid4

        memory = Memory(
            id=str(uuid4()),
            task="Test task",
            context="Test context",
            narrative="This is a test narrative",
            reflection="This is a test reflection",
            outcome="success",
            timestamp=datetime.now().isoformat(),
        )

        assert memory.task == "Test task"
        assert memory.outcome == "success"

    def test_pattern_creation(self):
        """Test creating a pattern."""
        from uuid import uuid4

        pattern = Pattern(
            id=str(uuid4()),
            description="Test pattern",
            confidence=0.9,
            success_rate=0.85,
            applications=5,
        )

        assert pattern.confidence == 0.9
        assert pattern.success_rate == 0.85
        assert pattern.applications == 5

    def test_execution_data(self):
        """Test execution data creation."""
        exec_data = ExecutionData(
            task="Test task",
            context="Test context",
            outcome="success",
            duration=2.5,
            description="Test description",
            error=None,
        )

        assert exec_data.task == "Test task"
        assert exec_data.outcome == "success"
        assert exec_data.duration == 2.5
