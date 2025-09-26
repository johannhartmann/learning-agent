"""Learning tool registry (currently empty)."""

from langchain_core.tools import BaseTool


def create_learning_tools() -> list[BaseTool]:
    """Return learning-specific tools exposed to the agent.

    All learning now happens automatically inside the orchestration layer,
    so the agent does not expose dedicated learning tools.
    """

    return []
