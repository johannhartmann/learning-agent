"""Integration tests for the Learning Agent system."""

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from learning_agent.agent import create_learning_agent
from learning_agent.learning.narrative_learner import NarrativeLearner


if TYPE_CHECKING:
    from learning_agent.state import LearningAgentState


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestNarrativeLearner:
    """Test narrative learner functionality."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
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
    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
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


class TestDeepAgentsIntegration:
    """Test deepagents integration."""

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("<") or not os.getenv("OPENAI_API_KEY"),
        reason="Requires valid API key",
    )
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
        }

        result = await agent.ainvoke(initial_state)

        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1


class TestSandboxIntegration:
    """Integration tests for the Python sandbox tool."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_SANDBOX_TESTS", "true").lower() == "true",
        reason="Sandbox tests require Deno runtime",
    )
    async def test_sandbox_tool_in_agent(self, temp_storage):
        """Test that sandbox tool is properly integrated in the agent."""
        # Create agent with sandbox tool
        agent = create_learning_agent(storage_path=temp_storage)

        # Check that sandbox tool is in the agent's tools
        tool_names = [tool.name for tool in agent.tools]
        assert "python_sandbox" in tool_names

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SKIP_SANDBOX_TESTS", "true").lower() == "true",
        reason="Sandbox tests require Deno runtime",
    )
    async def test_agent_can_use_sandbox(self, temp_storage):
        """Test that the agent can execute code in the sandbox."""
        agent = create_learning_agent(storage_path=temp_storage)

        # For integration testing, we verify the sandbox tool is available
        # Full execution would require LLM API calls
        sandbox_tool = None
        for tool in agent.tools:
            if tool.name == "python_sandbox":
                sandbox_tool = tool
                break

        assert sandbox_tool is not None
        assert sandbox_tool.description is not None
        assert "Python code" in sandbox_tool.description
        assert "sandbox" in sandbox_tool.description.lower()
