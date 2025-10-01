"""Integration tests for the deepagents-based Learning Agent."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from learning_agent.agent import create_learning_agent
from learning_agent.learning.narrative_learner import NarrativeLearner


if TYPE_CHECKING:
    from learning_agent.state import LearningAgentState


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

    def test_state_fields(self):
        """Basic smoke check for LearningAgentState typing."""
        state: LearningAgentState = {
            "messages": [],
            "todos": [],
            "files": {},
        }

        assert "messages" in state
