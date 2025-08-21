"""Integration tests for the Learning Agent system."""

import tempfile
from pathlib import Path

import pytest

import learning_agent.config
from learning_agent.agents import SubAgent, SubAgentConfig, SubAgentPool
from learning_agent.config import Settings
from learning_agent.learning import NarrativeLearner
from learning_agent.orchestration import Orchestrator, TodoItem, TodoStatus
from learning_agent.supervisor import Supervisor
from learning_agent.tools import FilesystemTool, PlanningTool


@pytest.fixture
def test_config():
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Settings(
            learning_db_path=Path(tmpdir) / ".agent",
            debug_mode=True,
            enable_learning=True,
            max_parallel_agents=3,
        )
        config.ensure_directories()
        yield config


@pytest.fixture
def episodic_memory(test_config):
    """Create test episodic memory."""
    # Temporarily update global settings
    original_settings = Settings()
    learning_agent.config.settings = test_config

    memory = NarrativeLearner()

    # Restore original settings after test
    yield memory
    learning_agent.config.settings = original_settings


class TestNarrativeLearner:
    """Test narrative learner functionality."""

    @pytest.mark.asyncio
    async def test_get_quick_context(self, episodic_memory):
        """Test getting quick context for a task."""
        # Get quick context should always work even with no memories
        context = await episodic_memory.get_quick_context("Test task")

        assert isinstance(context, dict)
        assert "has_prior_experience" in context
        assert "recent_memories" in context
        assert isinstance(context["recent_memories"], list)

    @pytest.mark.asyncio
    async def test_schedule_learning(self, episodic_memory):
        """Test scheduling post-execution learning."""
        execution_data = {
            "task": "Test task",
            "context": None,
            "outcome": "success",
            "duration": 1.5,
            "description": "Test completed successfully",
            "error": None,
        }

        # This should not raise an exception
        episodic_memory.schedule_post_execution_learning(execution_data)

        # Give it a moment to process
        import asyncio

        await asyncio.sleep(0.1)

        # Verify the background processor is running
        assert episodic_memory._background_started is True


class TestOrchestrator:
    """Test orchestration functionality."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel todo execution."""
        orchestrator = Orchestrator()

        todos = [
            TodoItem(content="Task 1", priority=5),
            TodoItem(content="Task 2", priority=3),
            TodoItem(content="Task 3", priority=7, dependencies=[]),
        ]

        result = await orchestrator.orchestrate(todos)

        assert "completed" in result
        assert "failed" in result
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_dependency_analysis(self):
        """Test dependency analysis."""
        orchestrator = Orchestrator()

        # Create todos with dependencies
        todo1 = TodoItem(id="t1", content="Task 1")
        todo2 = TodoItem(id="t2", content="Task 2", dependencies=["t1"])
        todo3 = TodoItem(id="t3", content="Task 3", dependencies=["t2"])

        state = {"todos": [todo1, todo2, todo3], "completed_todos": [], "messages": []}

        result = await orchestrator.analyze_dependencies(state)

        # Only todo1 should be ready initially
        ready = [t for t in result["todos"] if t.status == TodoStatus.IN_PROGRESS]
        assert len(ready) == 1
        assert ready[0].id == "t1"


class TestSubAgent:
    """Test sub-agent functionality."""

    @pytest.mark.asyncio
    async def test_sub_agent_execution(self):
        """Test sub-agent task execution."""
        config = SubAgentConfig(name="TestAgent", max_iterations=3, timeout_seconds=10)

        agent = SubAgent(config)
        result = await agent.execute("Simple test task")

        assert result.status in ["success", "failure", "timeout"]
        assert result.agent_id == agent.agent_id
        assert result.task == "Simple test task"
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_agent_pool(self):
        """Test agent pool parallel execution."""
        pool = SubAgentPool(max_agents=3)

        tasks = ["Task A", "Task B", "Task C"]

        results = await pool.execute_parallel(tasks)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.task == tasks[i]
            assert result.status in ["success", "failure", "timeout"]


class TestTools:
    """Test tool functionality."""

    def test_planning_tool(self):
        """Test planning tool operations."""
        tool = PlanningTool()

        # Create todos
        result1 = tool._run("create", content="First task", priority=5)
        assert "Created todo" in result1

        result2 = tool._run("create", content="Second task", priority=3)
        assert "Created todo" in result2

        # List todos
        result3 = tool._run("list")
        assert "First task" in result3
        assert "Second task" in result3

        # Prioritize
        result4 = tool._run("prioritize")
        assert "Execution order" in result4

    def test_filesystem_tool(self):
        """Test filesystem tool operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FilesystemTool(base_path=Path(tmpdir))

            # Write file
            result1 = tool._run("write", "test.txt", content="Hello World")
            assert "Wrote" in result1

            # Read file
            result2 = tool._run("read", "test.txt")
            assert result2 == "Hello World"

            # List directory
            result3 = tool._run("list_dir", ".")
            assert "test.txt" in result3

            # Delete file
            result4 = tool._run("delete", "test.txt")
            assert "Deleted" in result4


class TestSupervisor:
    """Test supervisor functionality."""

    @pytest.mark.asyncio
    async def test_task_processing(self, monkeypatch):
        """Test supervisor task processing."""
        # Mock API key for testing (use generic API_KEY)
        monkeypatch.setenv("API_KEY", "test-key")
        monkeypatch.setenv("LLM_PROVIDER", "fake")  # Use fake provider for testing

        supervisor = Supervisor()

        # Simple task that doesn't require actual LLM
        # Will either succeed with real API key or fail with test key
        result = await supervisor.process_task("Test task")

        # Should return a result (either success or error)
        assert "status" in result
        assert result["status"] in ["success", "error"]
        assert "task" in result
        assert result["task"] == "Test task"

    def test_supervisor_state(self):
        """Test supervisor state management."""
        supervisor = Supervisor()

        # Initial state
        assert supervisor.state.current_task is None
        assert len(supervisor.state.todos) == 0

        # Reset state
        supervisor.reset()
        assert supervisor.state.current_task is None


@pytest.mark.asyncio
async def test_end_to_end_simple():
    """Test simple end-to-end workflow."""
    # This would require API keys to fully test
    # For now, just verify components can be instantiated

    try:
        supervisor = Supervisor()
        assert supervisor is not None

        orchestrator = Orchestrator()
        assert orchestrator is not None

        episodic_memory = NarrativeLearner()
        assert episodic_memory is not None

        pool = SubAgentPool(max_agents=2)
        assert pool is not None

    except Exception as e:
        # Expected if API keys are not set
        assert "api" in str(e).lower() or "key" in str(e).lower()
