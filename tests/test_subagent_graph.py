from langchain_core.tools import tool
from unittest.mock import patch

from learning_agent.subagents import LEARNING_SUBAGENTS, build_learning_subagents


def test_research_subagent_configuration() -> None:
    names = {s["name"] for s in LEARNING_SUBAGENTS}
    assert "research-agent" in names

    research = next(s for s in LEARNING_SUBAGENTS if s["name"] == "research-agent")
    assert research["name"] == "research-agent"
    assert "You are a specialized research agent." in research["prompt"]


def test_subagent_prompts_unchanged() -> None:
    names = {s["name"] for s in LEARNING_SUBAGENTS}
    assert names == {"research-agent"}


def test_research_subagent_has_custom_graph() -> None:
    @tool
    def dummy_tool() -> str:
        """Dummy tool for testing."""
        return "ok"

    with patch("learning_agent.subagents.create_react_agent", return_value="dummy_graph") as mock:
        subs = build_learning_subagents(
            model=object(),
            tools=[],
            exclusive_tools={"research-agent": [dummy_tool]},
        )
        research = next(s for s in subs if s["name"] == "research-agent")
        assert research.get("graph") == "dummy_graph"
        mock.assert_called_once()
