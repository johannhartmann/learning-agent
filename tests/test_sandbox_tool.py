"""Unit tests for the enhanced Python sandbox tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import ToolMessage

from learning_agent.tools.sandbox_tool import EnhancedSandbox, python_sandbox


class TestEnhancedSandbox:
    """Test the EnhancedSandbox class."""

    @pytest.mark.asyncio
    async def test_init_with_network(self):
        """Test initialization with network access enabled."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool") as mock_tool:
            sandbox = EnhancedSandbox(allow_network=True)
            mock_tool.assert_called_once_with(stateful=True, allow_net=True)
            assert sandbox.session_state is None

    @pytest.mark.asyncio
    async def test_init_without_network(self):
        """Test initialization with network access disabled."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool") as mock_tool:
            sandbox = EnhancedSandbox(allow_network=False)
            mock_tool.assert_called_once_with(stateful=True, allow_net=False)
            assert sandbox.session_state is None

    @pytest.mark.asyncio
    async def test_wrap_code_for_viz(self):
        """Test code wrapping for visualization capture."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool"):
            sandbox = EnhancedSandbox()
            code = 'print("hello")'
            wrapped = sandbox._wrap_code_for_viz(code)

            # Check that the wrapper includes essential components
            assert "import matplotlib" in wrapped
            assert "import pandas" in wrapped
            assert "_captured_outputs" in wrapped
            assert 'print("hello")' in wrapped
            assert "json.dumps(_result)" in wrapped

    @pytest.mark.asyncio
    async def test_wrap_code_with_triple_quotes(self):
        """Test code wrapping with triple quotes in the code."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool"):
            sandbox = EnhancedSandbox()
            code = '"""This is a docstring"""\nprint("test")'
            wrapped = sandbox._wrap_code_for_viz(code)

            # Should handle triple quotes properly
            assert '\\"\\"\\"' in wrapped or '"""' not in wrapped
            assert 'print("test")' in wrapped

    @pytest.mark.asyncio
    async def test_parse_outputs_json_success(self):
        """Test parsing JSON outputs from sandbox execution."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool"):
            sandbox = EnhancedSandbox()
            result_json = json.dumps(
                {
                    "stdout": "Hello, world!",
                    "outputs": {
                        "images": [{"type": "matplotlib", "base64": "abc123"}],
                        "tables": [{"name": "df", "shape": [5, 3]}],
                        "data": {"key": "value"},
                    },
                }
            )

            parsed = sandbox._parse_outputs(result_json, "test_code")

            assert parsed["success"] is True
            assert parsed["code"] == "test_code"
            assert parsed["stdout"] == "Hello, world!"
            assert len(parsed["images"]) == 1
            assert parsed["images"][0]["type"] == "matplotlib"
            assert len(parsed["tables"]) == 1
            assert parsed["tables"][0]["name"] == "df"
            assert parsed["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_parse_outputs_fallback(self):
        """Test parsing non-JSON outputs (fallback mode)."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool"):
            sandbox = EnhancedSandbox()
            result = "Simple text output"

            parsed = sandbox._parse_outputs(result, "test_code")

            assert parsed["success"] is True
            assert parsed["code"] == "test_code"
            assert parsed["stdout"] == "Simple text output"
            assert parsed["stderr"] == ""
            assert parsed["images"] == []
            assert parsed["tables"] == []
            assert parsed["data"] == {}

    @pytest.mark.asyncio
    async def test_execute_with_viz_success(self):
        """Test successful code execution with visualization."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool"):
            sandbox = EnhancedSandbox()

            # Mock the sandbox tool
            mock_result = json.dumps(
                {
                    "stdout": "Execution complete",
                    "outputs": {"images": [], "tables": [], "data": {}},
                }
            )
            sandbox.sandbox = AsyncMock()
            sandbox.sandbox.ainvoke = AsyncMock(return_value=mock_result)

            result = await sandbox.execute_with_viz("print('test')")

            assert result["success"] is True
            assert result["stdout"] == "Execution complete"
            assert result["code"] == "print('test')"
            sandbox.sandbox.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test sandbox reset functionality."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandboxTool") as mock_tool:
            sandbox = EnhancedSandbox()
            sandbox.session_state = {"some": "state"}

            await sandbox.reset()

            # Should create a new sandbox instance
            assert mock_tool.call_count == 2  # Once in __init__, once in reset
            assert sandbox.session_state is None


class TestPythonSandboxTool:
    """Test the python_sandbox tool function."""

    @pytest.mark.asyncio
    async def test_python_sandbox_basic_execution(self):
        """Test basic code execution through the tool."""
        # Mock the sandbox
        with patch("learning_agent.tools.sandbox_tool.get_sandbox") as mock_get_sandbox:
            mock_sandbox = AsyncMock()
            mock_sandbox.execute_with_viz = AsyncMock(
                return_value={
                    "success": True,
                    "stdout": "Hello from sandbox",
                    "stderr": "",
                    "images": [],
                    "tables": [],
                    "data": {},
                    "code": "print('hello')",
                }
            )
            mock_get_sandbox.return_value = mock_sandbox

            # Create mock state and call the tool
            mock_state = {"messages": []}
            result = await python_sandbox.ainvoke(
                {
                    "code": "print('hello')",
                    "state": mock_state,
                    "tool_call_id": "test_id",
                    "reset_state": False,
                }
            )

            # Check the command result - Command object has update attribute
            assert hasattr(result, "update")
            assert "messages" in result.update
            messages = result.update["messages"]
            assert len(messages) == 1
            assert isinstance(messages[0], ToolMessage)
            assert "Hello from sandbox" in messages[0].content

    @pytest.mark.asyncio
    async def test_python_sandbox_with_reset(self):
        """Test code execution with sandbox reset."""
        with patch("learning_agent.tools.sandbox_tool.get_sandbox") as mock_get_sandbox:
            mock_sandbox = AsyncMock()
            mock_sandbox.reset = AsyncMock()
            mock_sandbox.execute_with_viz = AsyncMock(
                return_value={
                    "success": True,
                    "stdout": "Reset and executed",
                    "stderr": "",
                    "images": [],
                    "tables": [],
                    "data": {},
                    "code": "print('reset')",
                }
            )
            mock_get_sandbox.return_value = mock_sandbox

            mock_state = {"messages": []}
            await python_sandbox.ainvoke(
                {
                    "code": "print('reset')",
                    "state": mock_state,
                    "tool_call_id": "test_id",
                    "reset_state": True,
                }
            )

            # Should have called reset
            mock_sandbox.reset.assert_called_once()
            mock_sandbox.execute_with_viz.assert_called_once()

    @pytest.mark.asyncio
    async def test_python_sandbox_with_visualizations(self):
        """Test code execution that generates visualizations."""
        with patch("learning_agent.tools.sandbox_tool.get_sandbox") as mock_get_sandbox:
            mock_sandbox = AsyncMock()
            mock_sandbox.execute_with_viz = AsyncMock(
                return_value={
                    "success": True,
                    "stdout": "Plot created",
                    "stderr": "",
                    "images": [{"type": "matplotlib", "format": "png", "base64": "abc123"}],
                    "tables": [{"name": "df", "shape": [10, 3]}],
                    "data": {},
                    "code": "import matplotlib",
                }
            )
            mock_get_sandbox.return_value = mock_sandbox

            mock_state = {"messages": []}
            result = await python_sandbox.ainvoke(
                {
                    "code": "import matplotlib",
                    "state": mock_state,
                    "tool_call_id": "test_id",
                    "reset_state": False,
                }
            )

            # Command object has update attribute
            messages = result.update["messages"]
            content = messages[0].content

            # Should mention the generated visualizations
            assert "Generated 1 image(s)" in content
            assert "matplotlib" in content
            assert "Generated 1 table(s)" in content
            assert "10 rows x 3 columns" in content

    @pytest.mark.asyncio
    async def test_python_sandbox_error_handling(self):
        """Test error handling in sandbox execution."""
        with patch("learning_agent.tools.sandbox_tool.get_sandbox") as mock_get_sandbox:
            mock_sandbox = AsyncMock()
            mock_sandbox.execute_with_viz = AsyncMock(side_effect=Exception("Sandbox error"))
            mock_get_sandbox.return_value = mock_sandbox

            mock_state = {"messages": []}
            result = await python_sandbox.ainvoke(
                {
                    "code": "bad_code",
                    "state": mock_state,
                    "tool_call_id": "test_id",
                    "reset_state": False,
                }
            )

            # Command object has update attribute
            messages = result.update["messages"]
            assert len(messages) == 1
            assert "Sandbox execution error" in messages[0].content
            assert "Sandbox error" in messages[0].content


class TestSandboxSingleton:
    """Test the singleton pattern for sandbox instance."""

    def test_get_sandbox_singleton(self):
        """Test that get_sandbox returns the same instance."""
        with patch("learning_agent.tools.sandbox_tool.EnhancedSandbox") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Import and clear the global instance
            import learning_agent.tools.sandbox_tool as module
            from learning_agent.tools.sandbox_tool import get_sandbox

            module._sandbox_instance = None

            # First call should create instance
            sandbox1 = get_sandbox()
            assert sandbox1 == mock_instance
            mock_class.assert_called_once_with(allow_network=True)

            # Second call should return same instance
            sandbox2 = get_sandbox()
            assert sandbox2 == sandbox1
            assert mock_class.call_count == 1  # Still only called once
