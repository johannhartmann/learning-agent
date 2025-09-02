#!/usr/bin/env python3
"""Docker integration test for matplotlib issues in LangGraph agent.

This test ensures that the learning agent can properly execute matplotlib code
through the sandbox tool without the common import errors.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from learning_agent.agent import create_learning_agent


class TestDockerMatplotlibIntegration:
    """Test matplotlib functionality through the full LangGraph agent stack."""

    @pytest.fixture
    async def agent_with_memory(self, tmp_path):
        """Create a learning agent with memory for testing."""
        storage_path = tmp_path / "test_storage"
        storage_path.mkdir(exist_ok=True)

        # Create agent with memory saver for state persistence
        memory = MemorySaver()
        agent = create_learning_agent(storage_path=str(storage_path), memory=memory)
        return agent, memory

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.docker
    async def test_agent_matplotlib_execution(self, agent_with_memory):
        """Test that the agent can execute matplotlib code without import errors.

        This is the key test that verifies our fix for the matplotlib.pyplot
        import issue that causes infinite loops.
        """
        agent, memory = agent_with_memory

        # Request the agent to create a matplotlib plot
        messages = [
            HumanMessage(
                content="""
            Use the python_sandbox tool to create a simple matplotlib plot.
            The code should:
            1. Import matplotlib.pyplot as plt
            2. Create data: x = [1, 2, 3, 4], y = [1, 4, 9, 16]
            3. Create a plot with plt.plot(x, y)
            4. Add title "Test Plot"
            5. Print "Plot created successfully"

            Make sure to actually execute this in the sandbox, not just write the code.
            """
            )
        ]

        # Invoke the agent
        config = {"configurable": {"thread_id": "test-matplotlib"}}

        # Run the agent with a timeout
        result = None
        start_time = time.time()
        timeout = 30  # 30 seconds timeout

        async for event in agent.astream_events(
            {"messages": messages}, config=config, version="v2"
        ):
            if time.time() - start_time > timeout:
                pytest.fail("Agent execution timed out - possible infinite loop!")

            # Look for tool calls to python_sandbox
            if event["event"] == "on_tool_end" and event["name"] == "python_sandbox":
                result = event["data"]["output"]
                break

        # Verify the result
        assert result is not None, "Agent did not execute python_sandbox tool"

        # Check that execution was successful
        if isinstance(result, dict):
            assert (
                result.get("success") is True
            ), f"Sandbox execution failed: {result.get('stderr')}"
            assert "Plot created successfully" in result.get("stdout", "")
            # Should NOT have matplotlib.pyplot import errors
            assert "No module named 'matplotlib.pyplot'" not in result.get("stderr", "")
        elif isinstance(result, str):
            assert "Plot created successfully" in result
            assert "Error" not in result
            assert "No module named" not in result

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.docker
    async def test_agent_handles_matplotlib_retry(self, agent_with_memory):
        """Test that the agent can retry matplotlib code with error feedback.

        This verifies that our error feedback mechanism helps the agent
        avoid repeating the same mistakes.
        """
        agent, memory = agent_with_memory

        # First message - intentionally problematic code
        messages = [
            HumanMessage(
                content="""
            Use python_sandbox to run this exact code:
            ```python
            import matplotlib.pyplot
            matplotlib.pyplot.plot([1, 2], [1, 4])
            print("First attempt")
            ```

            If it fails, try again with a different approach.
            """
            )
        ]

        config = {"configurable": {"thread_id": "test-retry"}}

        tool_calls = []
        async for event in agent.astream_events(
            {"messages": messages}, config=config, version="v2"
        ):
            if event["event"] == "on_tool_end" and event["name"] == "python_sandbox":
                tool_calls.append(event["data"])  # noqa: PERF401

        # If our fix works, there should be at most 2 attempts (not infinite)
        assert len(tool_calls) <= 2, f"Too many retry attempts: {len(tool_calls)}"

        # The final attempt should succeed or agent should give up gracefully
        if len(tool_calls) > 0:
            last_result = tool_calls[-1].get("output", {})
            if isinstance(last_result, dict):
                # Either it succeeded or failed with clear error (not infinite loop)
                assert "success" in last_result

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.docker
    async def test_docker_environment_setup(self):
        """Verify Docker environment has correct setup for matplotlib."""
        # Check environment variables
        ts_source = os.environ.get("LANGCHAIN_SANDBOX_TS_SOURCE")
        if Path("/.dockerenv").exists():  # Running in Docker
            assert ts_source is not None, "TypeScript source not configured in Docker"
            assert ts_source.endswith(".ts"), f"Invalid TypeScript source: {ts_source}"

            # Verify the TypeScript file exists and has correct imports
            if Path(ts_source).exists():
                content = Path(ts_source).read_text()
                assert "jsr:" not in content, "TypeScript should not use JSR imports"
                assert "deno.land/std" in content, "TypeScript should use Deno.land URLs"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.docker
    async def test_agent_matplotlib_with_data_science(self, agent_with_memory):
        """Test matplotlib with pandas/numpy through the agent."""
        agent, memory = agent_with_memory

        messages = [
            HumanMessage(
                content="""
            Use python_sandbox to:
            1. Import pandas as pd, numpy as np, and matplotlib.pyplot as plt
            2. Create a DataFrame with random data:
               df = pd.DataFrame({'x': np.arange(10), 'y': np.random.randn(10)})
            3. Plot it: plt.plot(df['x'], df['y'])
            4. Print the DataFrame shape and "Data science libraries work!"
            """
            )
        ]

        config = {"configurable": {"thread_id": "test-datascience"}}

        result = None
        async for event in agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
            max_iterations=10,  # Prevent infinite loops
        ):
            if event["event"] == "on_tool_end" and event["name"] == "python_sandbox":
                result = event["data"]["output"]
                break

        assert result is not None, "Agent did not execute sandbox"

        if isinstance(result, dict):
            assert result.get("success") is True, f"Execution failed: {result.get('stderr')}"
            stdout = result.get("stdout", "")
            assert "Data science libraries work!" in stdout
            assert "(10, 2)" in stdout  # DataFrame shape


def run_docker_test():
    """Run the test in Docker environment."""
    # Build the Docker image if needed
    subprocess.run(
        ["docker-compose", "build", "server"], check=True, cwd=Path(__file__).parent.parent
    )

    # Run the test in Docker
    result = subprocess.run(
        [
            "docker-compose",
            "run",
            "--rm",
            "-e",
            "PYTHONPATH=/app/src",
            "server",
            "python",
            "-m",
            "pytest",
            "tests/test_docker_matplotlib.py",
            "-v",
            "-s",
            "-m",
            "docker",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # When run directly, execute in Docker
    if Path("/.dockerenv").exists():
        # Already in Docker, run tests directly
        pytest.main([__file__, "-v", "-s", "-m", "docker"])
    else:
        # Not in Docker, run tests in Docker container
        success = run_docker_test()
        sys.exit(0 if success else 1)
