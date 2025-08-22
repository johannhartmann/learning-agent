"""LangGraph server module for the learning agent."""

from langgraph.graph import END, StateGraph

from learning_agent.agent import create_learning_agent
from learning_agent.state import LearningAgentState


def create_graph():
    """Create the LangGraph graph for the learning agent.

    Returns:
        Compiled LangGraph graph ready to be served
    """
    # Create the deepagents-based agent
    agent = create_learning_agent()

    # Create a StateGraph with our custom state
    workflow = StateGraph(LearningAgentState)

    # Add the main agent node
    async def agent_node(state: LearningAgentState) -> LearningAgentState:
        """Main agent processing node."""
        result = await agent.ainvoke(state)  # type: ignore
        return result  # type: ignore

    workflow.add_node("agent", agent_node)

    # Set the entry point
    workflow.set_entry_point("agent")

    # Add edge from agent to END
    workflow.add_edge("agent", END)

    # Compile the graph
    return workflow.compile()


# Export the compiled graph for LangGraph server
graph = create_graph()
