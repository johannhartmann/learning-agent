"""LangGraph server module for the learning agent."""

from typing import Any

from langgraph.graph import END, StateGraph

from learning_agent.agent import create_learning_agent
from learning_agent.state import LearningAgentState


def create_graph() -> Any:
    """Create the LangGraph graph for the learning agent with automatic learning.

    Returns:
        Compiled LangGraph graph ready to be served with streaming and automatic learning
    """
    # Get the base deepagents agent
    agent = create_learning_agent()

    # Create a wrapper graph that adds automatic learning submission
    workflow = StateGraph(LearningAgentState)

    # Agent node - runs the main agent logic
    async def agent_node(state: LearningAgentState) -> dict[str, Any]:
        """Execute the main agent and return updated state."""
        # The agent is already a compiled graph, so we use ainvoke
        result = await agent.ainvoke(state)  # type: ignore
        return result  # type: ignore

    # Learning submission node - automatically submits conversations for learning
    async def submit_learning_node(state: LearningAgentState) -> LearningAgentState:
        """Submit the conversation for background learning via LangMem."""
        from learning_agent.learning.langmem_integration import get_learning_system

        messages = state.get("messages", [])

        # Only submit if there's meaningful conversation (more than just the initial human message)
        if messages and len(messages) > 1:
            learning_system = get_learning_system()

            # Check if any tasks were completed
            todos = state.get("todos", [])
            completed_tasks = [t for t in todos if t.get("status") == "completed"]

            # Use immediate processing (0 delay) since we learn at the end of conversations
            delay_seconds = 0

            # Submit to learning system and await completion
            await learning_system.submit_conversation_for_learning(
                messages=messages,
                delay_seconds=delay_seconds,
                metadata={
                    "thread_id": state.get("thread_id"),
                    "todos": todos,
                    "completed_count": len(completed_tasks),
                    "total_todos": len(todos) if todos else 0,
                },
            )

            # Log submission for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"Submitted conversation for learning: "
                f"{len(messages)} messages, "
                f"{len(completed_tasks)}/{len(todos) if todos else 0} tasks completed, "
                f"delay={delay_seconds}s"
            )

        # Return state unchanged - this is a side-effect only node
        return state

    # Add nodes to the graph
    workflow.add_node("agent", agent_node)
    workflow.add_node("submit_learning", submit_learning_node)

    # Define the flow
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", "submit_learning")
    workflow.add_edge("submit_learning", END)

    # Compile and return the graph
    return workflow.compile()


# Export the compiled graph for LangGraph server
graph = create_graph()
