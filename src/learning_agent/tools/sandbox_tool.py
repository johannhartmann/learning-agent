"""Enhanced Python sandbox tool with visualization support and error feedback."""

from typing import Annotated, Any

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langchain_sandbox.pyodide import PyodideSandbox
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from learning_agent.state import LearningAgentState


# Note: TypeScript source is now baked into Docker image via LANGCHAIN_SANDBOX_TS_PATH
# No need to patch at runtime - pyodide.py handles this correctly now


class EnhancedSandbox:
    """Enhanced sandbox with visualization and data output support."""

    def __init__(self, allow_network: bool = False):
        """Initialize the enhanced sandbox.

        Args:
            allow_network: Whether to allow network access for package installation
        """
        # Enable sandbox with network access control
        # Need to allow read/write access to Deno cache directory for pyodide files
        # Note: stateful=False to avoid dill dependency which isn't available in Pyodide
        self.sandbox = PyodideSandbox(  # type: ignore[call-arg]
            stateful=True,
            allow_net=allow_network,
            allow_read=[
                "/app/node_modules",
                "/app/node_modules/.deno",  # Deno cache directory for pyodide files
                "/opt/langchain_sandbox",
                "/data/src/ml/learning_agent/node_modules",  # Add local node_modules for testing
            ],
            allow_write=[
                "/app/node_modules",
                "/app/node_modules/.deno",  # Deno needs write for cache
                "/tmp",  # nosec B108 - Safe in isolated sandbox environment
            ],  # Deno needs to write to entire node_modules for cache
            return_files=True,  # IMPORTANT: Return files from virtual filesystem
            file_paths=["/tmp", "/sandbox", "."],  # nosec B108 - Safe in isolated sandbox environment
        )
        self.session_state = None

    async def execute_with_viz(self, code: str) -> dict[str, Any]:
        """Execute code with visualization capture.

        Args:
            code: Python code to execute

        Returns:
            Dictionary with stdout, stderr, files, and execution metadata
        """
        try:
            result = await self.sandbox.execute(code)
        except Exception as e:
            return {
                "success": False,
                "code": code,
                "stdout": "",
                "stderr": str(e),
                "files": [],
                "tables": [],
                "data": {},
            }

        # Get files from the sandbox's virtual filesystem
        files: list[str] = []
        files_data: dict[str, str] = {}

        # The PyodideSandbox result should have a files attribute with the virtual filesystem
        if hasattr(result, "files") and result.files:
            import base64

            for filepath, content in result.files.items():
                # Only track image files
                if any(
                    filepath.endswith(ext)
                    for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp", ".webp"]
                ):
                    files.append(filepath)
                    # Content is always bytes from PyodideSandbox
                    files_data[filepath] = base64.b64encode(content).decode("utf-8")

        return {
            "success": result.status == "success",
            "code": code,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "files": files,
            "files_data": files_data,  # Include actual file data from virtual filesystem
            "tables": [],
            "data": {},
        }

    async def reset(self) -> None:
        """Reset the sandbox state."""
        import asyncio

        # Create new sandbox in a thread to avoid blocking
        def create_new_sandbox() -> PyodideSandbox:
            # Need to allow read/write access to Deno cache directory for pyodide files
            return PyodideSandbox(  # type: ignore[call-arg]
                stateful=True,
                allow_net=False,
                allow_read=[
                    "/app/node_modules",
                    "/app/node_modules/.deno",  # Deno cache directory
                    "/opt/langchain_sandbox",
                ],
                allow_write=[
                    "/app/node_modules",
                    "/app/node_modules/.deno",  # Deno needs write for cache
                    "/tmp",  # nosec B108
                ],  # Deno needs to write to entire node_modules for cache
                return_files=True,  # IMPORTANT: Return files from virtual filesystem
                file_paths=["/tmp", "/sandbox", "."],  # Paths to check for files  # nosec B108
            )

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
    config: RunnableConfig,
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

        if result.get("files"):
            response_parts.append(f"\n**Generated {len(result['files'])} file(s):**\n")

            # Get thread_id from LangGraph config
            thread_id = config.get("configurable", {}).get("thread_id")
            for file_path in result["files"]:
                if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                    # Use absolute URL with thread_id in path so markdown parser accepts it
                    if thread_id:
                        file_url = (
                            f"http://localhost:10300/api/internal/files/{thread_id}{file_path}"
                        )
                    else:
                        file_url = f"http://localhost:10300/api/internal/files{file_path}"
                    response_parts.append(f"![{file_path.split('/')[-1]}]({file_url})\n")
                else:
                    response_parts.append(f"- {file_path}\n")

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

        # Store generated files in the agent state as base64-encoded data
        # This maintains complete isolation - files exist only in memory per session
        if result.get("files"):
            import base64

            # Get existing files from state or create new dict
            files = state.get("files", {})

            # Get the files_data with actual content from sandbox
            files_data = result.get("files_data", {})

            # Store files in state as base64-encoded data
            for file_path in result["files"]:
                if file_path in files_data:
                    try:
                        file_bytes = files_data[file_path]
                        # Ensure it's bytes
                        if isinstance(file_bytes, str):
                            # Already base64 (shouldn't happen with new API)
                            files[file_path] = file_bytes
                        elif isinstance(file_bytes, bytes):
                            # Encode bytes to base64 for storage in state
                            files[file_path] = base64.b64encode(file_bytes).decode("utf-8")
                        else:
                            # Convert to bytes if needed
                            file_bytes = bytes(file_bytes)
                            files[file_path] = base64.b64encode(file_bytes).decode("utf-8")

                        print(f"Stored file {file_path} in session memory")
                    except Exception as e:
                        print(f"Error storing file {file_path}: {e}")
                else:
                    print(f"File {file_path} has no data")

            state_updates["files"] = files

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
