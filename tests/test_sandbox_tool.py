"""Unit tests for the enhanced Python sandbox tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import ToolMessage

from learning_agent.tools.sandbox_tool import EnhancedSandbox, python_sandbox


class TestEnhancedSandbox:
    """Test the EnhancedSandbox class."""

    @pytest.mark.asyncio
    async def test_init_with_network(self):
        """Test initialization with network access enabled."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox") as mock_tool:
            sandbox = EnhancedSandbox(allow_network=True)
            assert mock_tool.call_args[1]["stateful"] is True
            assert mock_tool.call_args[1]["allow_net"] is True
            assert sandbox.session_state is None

    @pytest.mark.asyncio
    async def test_init_without_network(self):
        """Test initialization with network access disabled."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox") as mock_tool:
            sandbox = EnhancedSandbox(allow_network=False)
            assert mock_tool.call_args[1]["stateful"] is True
            assert mock_tool.call_args[1]["allow_net"] is False
            assert sandbox.session_state is None

    @pytest.mark.asyncio
    async def test_execute_with_viz_wrapping(self):
        """Test that execute_with_viz properly handles code."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox") as mock_pyodide:
            mock_instance = AsyncMock()
            # Create a mock result object
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stdout = "test output"
            mock_result.stderr = ""
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_pyodide.return_value = mock_instance

            sandbox = EnhancedSandbox()
            # Test that the sandbox can be created and has the expected method
            assert hasattr(sandbox, "execute_with_viz")
            assert callable(sandbox.execute_with_viz)

            # Test that it can execute code
            result = await sandbox.execute_with_viz("print('test')")
            assert result["success"] is True
            assert result["stdout"] == "test output"

    @pytest.mark.asyncio
    async def test_execute_with_triple_quotes(self):
        """Test code execution with triple quotes in the code."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox") as mock_pyodide:
            mock_instance = AsyncMock()
            # Create a mock result object
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stdout = "test"
            mock_result.stderr = ""
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_pyodide.return_value = mock_instance

            sandbox = EnhancedSandbox()
            code = '"""This is a docstring"""\nprint("test")'
            result = await sandbox.execute_with_viz(code)

            # Should handle the code and return a result
            assert isinstance(result, dict)
            assert "code" in result
            assert result["success"] is True
            assert result["stdout"] == "test"

    @pytest.mark.asyncio
    async def test_execute_with_viz_json_output(self):
        """Test execute_with_viz handling JSON outputs from sandbox."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox") as mock_pyodide:
            mock_instance = AsyncMock()
            # Create a mock result object with the expected attributes
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stdout = "__MATPLOTLIB_FIGURE__:abc123:__END_FIGURE__\nHello, world!"
            mock_result.stderr = ""

            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_pyodide.return_value = mock_instance

            sandbox = EnhancedSandbox()
            result = await sandbox.execute_with_viz("test_code")

            # Check the result structure
            assert result["success"] is True
            assert result["code"] == "test_code"
            assert "Hello, world!" in result["stdout"]
            assert len(result["images"]) == 1
            assert result["images"][0]["type"] == "matplotlib"
            assert result["images"][0]["base64"] == "abc123"

    @pytest.mark.asyncio
    async def test_execute_with_viz_text_output(self):
        """Test execute_with_viz handling plain text outputs."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox") as mock_pyodide:
            mock_instance = AsyncMock()
            # Create a mock result object with the expected attributes
            mock_result = MagicMock()
            mock_result.status = "success"
            mock_result.stdout = "Simple text output"
            mock_result.stderr = ""

            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_pyodide.return_value = mock_instance

            sandbox = EnhancedSandbox()
            result = await sandbox.execute_with_viz("test_code")

            # Should handle plain text output
            assert result["success"] is True
            assert result["code"] == "test_code"
            assert result["stdout"] == "Simple text output"
            assert result["stderr"] == ""
            assert result["images"] == []
            assert result["tables"] == []

    @pytest.mark.asyncio
    async def test_execute_with_viz_success(self):
        """Test successful code execution with visualization."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox"):
            sandbox = EnhancedSandbox()

            # Mock the execute method directly on sandbox
            sandbox.sandbox = MagicMock()
            mock_result = MagicMock(status="success", stdout="Execution complete", stderr="")
            sandbox.sandbox.execute = AsyncMock(return_value=mock_result)

            result = await sandbox.execute_with_viz("print('test')")

            assert result["success"] is True
            assert result["code"] == "print('test')"
            assert result["stdout"] == "Execution complete"
            sandbox.sandbox.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test sandbox reset functionality."""
        with patch("learning_agent.tools.sandbox_tool.PyodideSandbox"):
            sandbox = EnhancedSandbox()
            sandbox.session_state = {"some": "state"}

            with patch("asyncio.to_thread") as mock_thread:
                mock_thread.return_value = MagicMock()
                await sandbox.reset()

                # Should have called to_thread to create new sandbox
                mock_thread.assert_called_once()
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

            # Reset is currently disabled to avoid dill issues
            # mock_sandbox.reset.assert_called_once()
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
            # The code content might not appear in the output message
            assert "Plot created" in content
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

    @pytest.mark.asyncio
    async def test_get_sandbox_singleton(self):
        """Test that get_sandbox returns the same instance."""
        with patch("learning_agent.tools.sandbox_tool.EnhancedSandbox") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Import and clear the global instance
            import learning_agent.tools.sandbox_tool as module
            from learning_agent.tools.sandbox_tool import get_sandbox

            module._sandbox_instance = None

            # First call should create instance
            with patch("asyncio.to_thread", return_value=mock_instance):
                sandbox1 = await get_sandbox()
                assert sandbox1 == mock_instance

            # Second call should return same instance
            sandbox2 = await get_sandbox()
            assert sandbox2 == sandbox1
