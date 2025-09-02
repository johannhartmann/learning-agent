"""Enhanced Python sandbox tool with visualization support and error feedback."""

from typing import Annotated, Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_sandbox.pyodide import PyodideSandbox
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from learning_agent.state import LearningAgentState
from learning_agent.tools.sandbox_config import patch_pyodide_sandbox


# Ensure we're using the GitHub TypeScript source, not JSR
patch_pyodide_sandbox()


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
        # Execute the user code directly
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

# Maximum number of errors to keep in state
MAX_ERROR_HISTORY = 5


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
    state: Annotated[LearningAgentState, InjectedState],
    reset_state: bool = False,
) -> Command[Any]:
    """Execute Python code in a secure sandbox environment.

    CRITICAL: You MUST use print() to display output! The sandbox only shows what you print.

    PRE-INSTALLED PACKAGES:
    The following packages will be pre-installed by the sandbox infrastructure:
    - matplotlib, numpy, pandas, scipy, scikit-learn
    - bokeh, altair, sympy, networkx, statsmodels

    IMPORTANT: Do NOT manually install these pre-installed packages!
    They are already available. Simply import them directly:
    ```python
    import matplotlib as mpl
    import numpy as np
    import pandas as pd
    ```

    ADDITIONAL PACKAGES:
    For packages NOT in the pre-installed list, use micropip:
    ```python
    import micropip

    await micropip.install("package_name")
    import package_name
    ```

    ENVIRONMENT: This is a HEADLESS backend environment without display capabilities.
    - GUI operations and interactive displays are not supported
    - Save visualizations to files instead of trying to display them
    - matplotlib automatically uses the appropriate backend for headless operation
    - Never try to install matplotlib.pyplot

    Args:
        code: Python code to execute. Always use print() to show results.
        reset_state: If True, reset sandbox to clean state (default: False)

    Examples:
        # Using pre-installed numpy and matplotlib (NO installation needed!)
        import numpy as np
        import matplotlib as mpl

        x = np.linspace(0, 2*np.pi, 100)
        mpl.pyplot.plot(x, np.sin(x))
        mpl.pyplot.savefig('/tmp/plot.png')
        mpl.print("Plot saved successfully")

        # Using pre-installed pandas
        import pandas as pd
        df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        print(df.to_string())

        # Installing a package that's NOT pre-installed
        import micropip
        await micropip.install('requests')
        import requests
        response = requests.get('https://api.example.com')
        print(response.status_code)
    """
    sandbox = await get_sandbox()

    # Note: reset_state is currently disabled to avoid dill package installation
    # issues. The sandbox maintains state properly without explicit reset.
    # TODO: Re-enable when langchain-sandbox supports reset without dill
    _ = reset_state  # Acknowledge the parameter even though we don't use it

    # Get error history from state
    error_history = state.get("sandbox_error_history", [])

    # Check for previous similar errors
    code_snippet = code[:200]  # First 200 chars for comparison

    # Use list comprehension for better performance
    previous_errors = [
        error_entry["error"]
        for error_entry in error_history
        if (
            "import matplotlib.pyplot" in code
            and "matplotlib.pyplot" in error_entry.get("error", "")
        )
        or error_entry.get("code_snippet", "")[:100] in code
    ]

    try:
        # Execute code with visualization capture
        result = await sandbox.execute_with_viz(code)

        # Track errors for future reference in state
        state_updates = {}
        if not result["success"] and result.get("stderr"):
            new_error = {
                "code_snippet": code_snippet,
                "error": result["stderr"],
            }
            updated_history = [*error_history, new_error]
            # Keep only recent errors
            if len(updated_history) > MAX_ERROR_HISTORY:
                updated_history = updated_history[-MAX_ERROR_HISTORY:]
            state_updates["sandbox_error_history"] = updated_history

        # Format response message
        response_parts = []

        # IMPORTANT: Always show previous errors first if they exist
        if previous_errors:
            response_parts.append(
                "⚠️ **IMPORTANT - Previous Attempt Failed with Similar Code:**\n"
                "The following error occurred when similar code was tried before:\n"
                + "\n".join(f"```\n{err[:500]}\n```" for err in previous_errors[-2:])
                + "\n**Please use a different approach to avoid this error.**\n"
            )

        if result.get("stdout"):
            response_parts.append(f"**Output:**\n```\n{result['stdout']}\n```")

        if result.get("stderr"):
            response_parts.append(f"**Errors:**\n```\n{result['stderr']}\n```")

            # Add specific guidance for the matplotlib.pyplot error
            if "Failed to install required Python packages: matplotlib.pyplot" in result["stderr"]:
                response_parts.append(
                    "\n**Error Guidance:**\n"
                    "❌ The error shows you're trying to install 'matplotlib.pyplot' which doesn't exist.\n"
                    "✅ matplotlib is already pre-installed! Just use:\n"
                    "```python\n"
                    "import matplotlib.pyplot as plt\n"
                    "```\n"
                    "Do NOT use micropip to install matplotlib - it's already available!"
                )

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

        # Return the response message with state updates
        return Command(
            update={
                "messages": [ToolMessage(response, tool_call_id=tool_call_id)],
                **state_updates,  # Include state updates if there are any
            }
        )

    except Exception as e:
        error_msg = f"Sandbox execution error: {e!s}"
        return Command(update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]})


def create_sandbox_tool() -> Any:
    """Create the sandbox tool for the agent."""
    return python_sandbox
