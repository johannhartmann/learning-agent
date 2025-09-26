from learning_agent.agent import create_learning_agent
from learning_agent.subagents import LEARNING_SUBAGENTS


def test_research_subagent_registered():
    names = {s["name"] for s in LEARNING_SUBAGENTS}
    assert "research-agent" in names


def test_agent_builds_with_research_subagent():
    # Ensure the agent graph can be constructed with the new subagent
    agent = create_learning_agent()
    assert agent is not None

