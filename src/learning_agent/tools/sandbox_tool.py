"""Enhanced Python sandbox tool with visualization support."""

from typing import Annotated, Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_sandbox.pyodide import PyodideSandbox
from langgraph.types import Command


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
        # Check if code uses matplotlib and needs special handling
        uses_matplotlib = "matplotlib" in code or "plt" in code

        if uses_matplotlib:
            # Prepend matplotlib backend setup for Pyodide
            setup_code = """
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64

# Store original show function
_original_show = plt.show

# Override show to capture the figure
def _capture_show():
    import io
    import base64
    fig = plt.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    print(f"__MATPLOTLIB_FIGURE__:{img_str}:__END_FIGURE__")
    plt.close(fig)

plt.show = _capture_show
"""
            full_code = setup_code + "\n" + code
        else:
            full_code = code

        try:
            result = await self.sandbox.execute(full_code)
        except Exception as e:
            return {
                "success": False,
                "code": code,
                "stdout": "",
                "stderr": str(e),
                "images": [],
                "tables": [],
                "data": {},
            }

        # Parse output for matplotlib figures
        images: list[dict[str, Any]] = []
        stdout = result.stdout or ""

        if uses_matplotlib and "__MATPLOTLIB_FIGURE__:" in stdout:
            # Extract base64 images from stdout
            import re

            pattern = r"__MATPLOTLIB_FIGURE__:([^:]+):__END_FIGURE__"
            matches = re.findall(pattern, stdout)
            images.extend(
                {
                    "type": "matplotlib",
                    "format": "png",
                    "base64": match,
                }
                for match in matches
            )
            # Clean stdout by removing the figure markers
            stdout = re.sub(pattern, "", stdout).strip()

        return {
            "success": result.status == "success",
            "code": code,
            "stdout": stdout,
            "stderr": result.stderr or "",
            "images": images,
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
    tool_call_id: Annotated[str, InjectedToolCallId],
    reset_state: bool = False,
) -> Command[Any]:
    """Execute Python code in a secure sandbox environment.

    CRITICAL: You MUST use print() to display output! The sandbox only shows what you print.

    Args:
        code: Python code to execute. Always use print() to show results.
        reset_state: If True, reset sandbox to clean state (default: False)

    Examples:
        # Calculate factorial
        def factorial(n):
            if n <= 1:
                return 1
            return n * factorial(n - 1)

        print(f"Factorial of 5: {factorial(5)}")

        # String manipulation
        text = "hello world"
        print(f"Uppercase: {text.upper()}")
        print(f"Word count: {len(text.split())}")
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

        # Return the response message
        return Command(
            update={
                "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
            }
        )

    except Exception as e:
        error_msg = f"Sandbox execution error: {e!s}"
        return Command(update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]})


def create_sandbox_tool() -> Any:
    """Create the sandbox tool for the agent."""
    return python_sandbox
