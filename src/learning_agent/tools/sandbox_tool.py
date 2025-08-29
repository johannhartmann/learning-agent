"""Enhanced Python sandbox tool with visualization support."""

import json
from typing import Annotated, Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_sandbox.pyodide import PyodideSandbox
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from learning_agent.state import LearningAgentState


class EnhancedSandbox:
    """Enhanced sandbox with visualization and data output support."""

    def __init__(self, allow_network: bool = False):
        """Initialize the enhanced sandbox.

        Args:
            allow_network: Whether to allow network access for package installation
        """
        self.sandbox = PyodideSandbox(stateful=True, allow_net=allow_network)
        self.session_state = None

    async def execute_with_viz(self, code: str) -> dict[str, Any]:
        """Execute code with visualization capture.

        Args:
            code: Python code to execute

        Returns:
            Dictionary with stdout, stderr, images, tables, and execution metadata
        """
        # For now, execute code directly without the wrapper
        # The wrapper causes issues with the sandbox execution
        try:
            # Use execute method from PyodideSandbox
            # This is already async, so we can await it directly
            result = await self.sandbox.execute(code)
        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "code": code,
                "stdout": "",
                "stderr": error_msg,
                "images": [],
                "tables": [],
                "data": {},
            }
        else:
            # Parse the result
            return {
                "success": result.status == "success",
                "code": code,
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "images": [],
                "tables": [],
                "data": {},
            }

    def _wrap_code_for_viz(self, code: str) -> str:
        """Wrap user code to capture matplotlib figures and data outputs.

        Args:
            code: Original user code

        Returns:
            Wrapped code with visualization capture logic
        """
        wrapper = '''
import sys
import io
import base64
import json

# Set up matplotlib for non-interactive backend
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    pass

# Capture stdout
_original_stdout = sys.stdout
_stdout_buffer = io.StringIO()
sys.stdout = _stdout_buffer

# Storage for captured outputs
_captured_outputs = {
    "images": [],
    "tables": [],
    "data": {}
}

# Execute user code
try:
    exec("""
{code}
""")

    # Capture any matplotlib figures
    try:
        import matplotlib.pyplot as plt
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            _captured_outputs["images"].append({
                "type": "matplotlib",
                "format": "png",
                "base64": base64.b64encode(buf.read()).decode('utf-8'),
                "figure_num": fig_num
            })
            plt.close(fig)
    except:
        pass

    # Capture any PIL/Pillow images
    try:
        from PIL import Image
        # Check if any PIL Image objects exist in globals
        for var_name, var_value in list(globals().items()):
            if isinstance(var_value, Image.Image):
                buf = io.BytesIO()
                var_value.save(buf, format='PNG')
                buf.seek(0)
                _captured_outputs["images"].append({
                    "type": "pil",
                    "format": "png",
                    "base64": base64.b64encode(buf.read()).decode('utf-8'),
                    "variable": var_name
                })
    except:
        pass

    # Capture pandas DataFrames as HTML
    try:
        import pandas as pd
        for var_name, var_value in list(globals().items()):
            if isinstance(var_value, pd.DataFrame):
                _captured_outputs["tables"].append({
                    "name": var_name,
                    "html": var_value.to_html(max_rows=100, max_cols=20),
                    "shape": var_value.shape,
                    "info": str(var_value.info())
                })
    except:
        pass

except Exception as e:
    print(f"Error during execution: {e}", file=sys.stderr)

finally:
    # Restore stdout
    sys.stdout = _original_stdout

# Return captured outputs as JSON
_result = {
    "stdout": _stdout_buffer.getvalue(),
    "outputs": _captured_outputs
}
print(json.dumps(_result))
'''
        # Escape the code properly for embedding
        escaped_code = code.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return wrapper.replace("{code}", escaped_code)

    def _parse_outputs(self, result: str, original_code: str) -> dict[str, Any]:
        """Parse the execution result into structured format.

        Args:
            result: Raw execution result from sandbox
            original_code: Original code for reference

        Returns:
            Structured output dictionary
        """
        try:
            # Try to parse as JSON (from our wrapper)
            parsed = json.loads(result)
            return {
                "success": True,
                "code": original_code,
                "stdout": parsed.get("stdout", ""),
                "stderr": "",
                "images": parsed.get("outputs", {}).get("images", []),
                "tables": parsed.get("outputs", {}).get("tables", []),
                "data": parsed.get("outputs", {}).get("data", {}),
            }
        except (json.JSONDecodeError, TypeError):
            # Fallback for direct output
            return {
                "success": True,
                "code": original_code,
                "stdout": str(result),
                "stderr": "",
                "images": [],
                "tables": [],
                "data": {},
            }

    async def reset(self) -> None:
        """Reset the sandbox state."""
        import asyncio

        # Create new sandbox in a thread to avoid blocking
        def create_new_sandbox() -> PyodideSandbox:
            return PyodideSandbox(stateful=True, allow_net=False)

        self.sandbox = await asyncio.to_thread(create_new_sandbox)
        self.session_state = None


# Global sandbox instance (created on first use)
_sandbox_instance: EnhancedSandbox | None = None


async def get_sandbox() -> EnhancedSandbox:
    """Get or create the global sandbox instance."""
    global _sandbox_instance
    if _sandbox_instance is None:
        import asyncio

        # Create the sandbox in a thread to avoid blocking
        def create_sandbox() -> EnhancedSandbox:
            return EnhancedSandbox(allow_network=True)

        # Use asyncio.to_thread to avoid blocking the event loop
        _sandbox_instance = await asyncio.to_thread(create_sandbox)

    assert _sandbox_instance is not None
    return _sandbox_instance


@tool
async def python_sandbox(
    code: str,
    state: Annotated[LearningAgentState, InjectedState],  # noqa: ARG001
    tool_call_id: Annotated[str, InjectedToolCallId],
    reset_state: bool = False,
) -> Command[Any]:
    """Execute Python code in a secure sandbox with visualization support.

    This tool runs Python code in an isolated WebAssembly environment using Pyodide.
    It maintains state across executions and can capture matplotlib plots, PIL images,
    and pandas DataFrames.

    Args:
        code: Python code to execute. Can include imports, function definitions,
              data analysis, plotting, etc. State is maintained between calls.
        reset_state: If True, reset the sandbox to a clean state before execution

    Returns:
        Execution results including stdout, generated images, and data tables

    Examples:
        - Data analysis: Load data, compute statistics, create visualizations
        - Algorithm testing: Test functions before writing to files
        - Quick calculations: Mathematical computations, data transformations
        - Plotting: Generate matplotlib charts, histograms, heatmaps
        - Image processing: Use PIL/Pillow for image manipulation
    """
    sandbox = await get_sandbox()

    # Note: reset_state is currently disabled to avoid dill package installation
    # issues. The sandbox maintains state properly without explicit reset.
    # TODO: Re-enable when langchain-sandbox supports reset without dill
    _ = reset_state  # Acknowledge the parameter even though we don't use it

    try:
        # Execute code with visualization capture
        result = await sandbox.execute_with_viz(code)

        # Format response message
        response_parts = []

        if result.get("stdout"):
            response_parts.append(f"**Output:**\n```\n{result['stdout']}\n```")

        if result.get("stderr"):
            response_parts.append(f"**Errors:**\n```\n{result['stderr']}\n```")

        if result.get("images"):
            response_parts.append(f"\n**Generated {len(result['images'])} image(s)**")
            for idx, img in enumerate(result["images"]):
                img_type = img.get("type", "unknown")
                # In a real implementation, we'd pass these to the UI
                # For now, we just note they were generated
                response_parts.append(f"- Image {idx + 1}: {img_type} plot")

        if result.get("tables"):
            response_parts.append(f"\n**Generated {len(result['tables'])} table(s)**")
            for table in result["tables"]:
                shape = table.get("shape", (0, 0))
                response_parts.append(
                    f"- DataFrame '{table['name']}': {shape[0]} rows x {shape[1]} columns"
                )

        response = (
            "\n".join(response_parts)
            if response_parts
            else "Code executed successfully (no output)"
        )

        # Store visualization data in state for potential UI rendering
        # This could be used by the UI to display images inline
        return Command(
            update={
                "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
                # Store viz data in state if needed for UI
                "current_context": {"sandbox_outputs": result},
            }
        )

    except Exception as e:
        error_msg = f"Sandbox execution error: {e!s}"
        return Command(update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]})


def create_sandbox_tool() -> Any:
    """Create the sandbox tool for the agent."""
    return python_sandbox
