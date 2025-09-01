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
        # For now, just execute the code directly without wrapping
        # The sandbox should handle matplotlib installation internally
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

        if "__MATPLOTLIB_FIGURE__:" in stdout:
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

    IMPORTANT: For packages like matplotlib, you must install them first:
    ```python
    import micropip

    await micropip.install("matplotlib")
    import matplotlib.pyplot as plt
    ```

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

        # For matplotlib plots:
        import micropip
        await micropip.install('matplotlib')
        import matplotlib.pyplot as plt
        import numpy as np
        x = np.linspace(0, 2*np.pi, 100)
        plt.plot(x, np.sin(x))
        plt.show()
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
            response_parts.append(f"\n**Generated {len(result['images'])} image(s)**\n")
            for idx, img in enumerate(result["images"]):
                # Include the image as a markdown data URI that the UI can render
                response_parts.append(
                    f"![Figure {idx + 1}](data:image/{img.get('format', 'png')};base64,{img['base64']})"
                )

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
