"""LangGraph server module for the learning agent.

Configures a Postgres checkpointer for persistence so threads and state
survive restarts across container rebuilds.
"""

from typing import Any
import os

from langgraph.graph import END, StateGraph
import importlib, importlib.util
print("[persistence] find_spec(langgraph.checkpoint.postgres)=", importlib.util.find_spec("langgraph.checkpoint.postgres"), flush=True)
print("[persistence] find_spec(langgraph.checkpoint.postgres.aio)=", importlib.util.find_spec("langgraph.checkpoint.postgres.aio"), flush=True)
try:
    # Option A: Canonical Postgres saver import (no pin)
    from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore
except Exception:  # fallback to standalone package name, if used in this environment
    try:
        from langgraph_checkpoint_postgres import PostgresSaver  # type: ignore
    except Exception as _e:
        PostgresSaver = None  # type: ignore[assignment]
# Use Postgres-backed checkpointer for persistence.
# Prefer the dedicated Postgres saver; fall back to a generic SQLAlchemy saver
# if available in the current LangGraph version.
PostgresSaver = None  # type: ignore[assignment]
SQLAlchemySaver = None  # type: ignore[assignment]

def _try_import(name: str):  # pragma: no cover - helper
    try:
        if importlib.util.find_spec(name) is not None:
            return importlib.import_module(name)
    except Exception:
        return None
    return None

_pg_modules = [
    "langgraph.checkpoint.postgres",
    "langgraph.checkpoint.postgres.aio",
    "langgraph_checkpoint_postgres",
    "langgraph_checkpoint_postgres.saver",
]
_pg_classes = ["PostgresSaver", "AsyncPostgresSaver", "Saver"]
for _name in _pg_modules:
    _mod = _try_import(_name)
    if _mod is not None:
        print(f"[persistence] Found Postgres module: {_name}", flush=True)
        for _cls in _pg_classes:
            PostgresSaver = getattr(_mod, _cls, None)
            if PostgresSaver is not None:
                print(f"[persistence] Using Postgres saver class: {_cls}", flush=True)
                break
    if PostgresSaver is not None:
        break

_sql_modules = [
    "langgraph.checkpoint.sql",
    "langgraph.checkpoint.sqlalchemy",
    "langgraph_checkpoint.sql",
    "langgraph_checkpoint.sqlalchemy",
]
_sql_classes = ["SQLAlchemySaver", "Saver"]
for _name in _sql_modules:
    _mod = _try_import(_name)
    if _mod is not None:
        print(f"[persistence] Found SQL module: {_name}", flush=True)
        for _cls in _sql_classes:
            SQLAlchemySaver = getattr(_mod, _cls, None)
            if SQLAlchemySaver is not None:
                print(f"[persistence] Using SQLAlchemy saver class: {_cls}", flush=True)
                break
    if SQLAlchemySaver is not None:
        break

from learning_agent.agent import create_learning_agent
from learning_agent.state import LearningAgentState


def create_graph() -> Any:
    """Create the LangGraph graph for the learning agent with automatic learning and A2A support.

    Returns:
        Compiled LangGraph graph ready to be served with streaming, A2A, and automatic learning
    """
    # Get the base deepagents agent
    from typing import cast

    agent = create_learning_agent()

    # Create a wrapper graph that adds automatic learning submission and A2A support
    workflow = StateGraph(LearningAgentState)

    # A2A preprocessing node - handles incoming A2A requests
    async def a2a_preprocessor(state: LearningAgentState) -> dict[str, Any]:
        """Process incoming A2A requests if present."""
        from learning_agent.a2a_handler import process_a2a_request

        # Check if this is an A2A request (has jsonrpc field)
        if isinstance(state, dict) and "jsonrpc" in state:
            # Process as A2A request
            return await process_a2a_request(state, state)

        # Not an A2A request, pass through
        return state

    # IMPORTANT: Add the agent graph directly to preserve streaming events.
    # Wrapping the agent in an async function (await agent.ainvoke) collapses
    # intermediate events into a single step and prevents incremental updates.

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
    workflow.add_node("a2a_preprocessor", a2a_preprocessor)
    workflow.add_node("agent", cast(Any, agent))
    workflow.add_node("submit_learning", submit_learning_node)

    # Define the flow
    workflow.set_entry_point("a2a_preprocessor")
    workflow.add_edge("a2a_preprocessor", "agent")
    workflow.add_edge("agent", "submit_learning")
    workflow.add_edge("submit_learning", END)

    # Configure a Postgres checkpointer for persistence
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://learning_agent:learning_agent_pass@postgres:5432/learning_memories",
    )
    # Ensure sync driver for psycopg3 if DSN is generic
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    if PostgresSaver is None:
        raise RuntimeError(
            "Postgres checkpointer not available. Ensure 'langgraph-checkpoint-postgres' is installed "
            "in the server image and rebuild."
        )

    # PostgresSaver API shim: support minor naming differences
    if hasattr(PostgresSaver, "from_conn_string"):
        checkpointer = PostgresSaver.from_conn_string(db_url)  # type: ignore[attr-defined]
    elif hasattr(PostgresSaver, "from_url"):
        checkpointer = PostgresSaver.from_url(db_url)  # type: ignore[attr-defined]
    else:
        checkpointer = PostgresSaver(db_url)  # type: ignore[call-arg]

    # IMPORTANT: Run setup once to ensure tables/migrations exist
    try:
        if hasattr(checkpointer, "setup"):
            checkpointer.setup()  # type: ignore[attr-defined]
    except Exception:
        # If setup fails at runtime, graph will likely error later; surface clearly
        import logging

        logging.getLogger(__name__).exception("Postgres checkpointer setup() failed")

    # Compile and return the graph with persistence
    return workflow.compile(checkpointer=checkpointer)


# Export the compiled graph for LangGraph server
graph = create_graph()
