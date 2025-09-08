"""LangGraph server module for the learning agent.

Configures a Postgres checkpointer for persistence so threads and state
survive restarts across container rebuilds. Exposes an ASGI app that serves
the LangGraph API in-process (no external platform/Redis required).
"""

import importlib
import importlib.util
import os
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, StateGraph

from learning_agent.agent import create_learning_agent
from learning_agent.state import LearningAgentState


if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Callable


print(
    "[persistence] find_spec(langgraph.checkpoint.postgres)=",
    importlib.util.find_spec("langgraph.checkpoint.postgres"),
    flush=True,
)
print(
    "[persistence] find_spec(langgraph.checkpoint.postgres.aio)=",
    importlib.util.find_spec("langgraph.checkpoint.postgres.aio"),
    flush=True,
)
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


def _build_langgraph_app(graph: Any) -> Any:
    """Attempt to construct a LangGraph API ASGI app for the given graph.

    Tries multiple import paths to accommodate minor packaging differences.
    """
    create_app: Callable[..., Any] | None = None

    # Ensure langgraph_api can import without failing on missing env
    # Prefer a plain Postgres URI for the platform's expected config
    default_plain = (
        "postgresql://learning_agent:learning_agent_pass@postgres:5432/learning_memories"
    )
    db_plain = os.environ.get("DATABASE_URI") or os.environ.get("DATABASE_URL") or default_plain
    os.environ.setdefault("DATABASE_URI", db_plain)
    os.environ.setdefault("LANGGRAPH_RUNTIME_EDITION", "postgres")
    os.environ.setdefault("REDIS_URI", os.environ.get("REDIS_URI", "memory://"))

    # Try the common import paths for langgraph-api
    app = None
    for mod_path in (
        "langgraph_api.server",
        "langgraph_api",
        "langgraph_server",
    ):
        mod = _try_import(mod_path)
        if mod is None:
            continue
        # Preferred: a factory
        create_app = getattr(mod, "create_app", None)
        if callable(create_app):
            print(f"[server] Using create_app from: {mod_path}", flush=True)
            app = create_app(graphs={"learning_agent": graph})  # type: ignore[call-arg]
            break
        # Fallback: module exports a prebuilt Starlette app
        module_app = getattr(mod, "app", None)
        if module_app is not None:
            print(f"[server] Using module.app from: {mod_path}", flush=True)
            app = module_app
            break

    if app is None:
        raise RuntimeError("Could not obtain ASGI app from langgraph-api")

    # Add permissive CORS for local UI/dev usage
    try:
        from starlette.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
        )
    except Exception:
        pass

    # Add a simple health endpoint used by docker-compose healthcheck
    try:
        # FastAPI-compatible
        if hasattr(app, "get"):
            app.get("/health")(lambda: {"status": "ok"})  # type: ignore[misc]
        else:
            # Starlette-compatible
            from starlette.responses import JSONResponse  # type: ignore

            def _health(_request):  # type: ignore
                return JSONResponse({"status": "ok"})

            if hasattr(app, "add_route"):
                app.add_route("/health", _health)  # type: ignore[attr-defined]
    except Exception:
        pass

    # Register our compiled graph during app lifespan (event loop available)
    try:
        from contextlib import asynccontextmanager

        import langgraph_api.graph as api_graph  # type: ignore

        graph_id = os.environ.get("NEXT_PUBLIC_AGENT_ID", "learning_agent")

        original_lifespan = getattr(app.router, "lifespan_context", None)

        @asynccontextmanager
        async def combined_lifespan(a):  # type: ignore
            if original_lifespan:
                cm = original_lifespan(a)
            else:
                # dummy context manager
                @asynccontextmanager
                async def _noop(_):
                    yield

                cm = _noop(a)

            async with cm:
                try:
                    await api_graph.register_graph(graph_id=graph_id, graph=graph, config=None)
                    print(
                        f"[server] Registered graph '{graph_id}' with langgraph_api runtime",
                        flush=True,
                    )
                except Exception as e:
                    print(f"[server] Graph registration failed: {e}", flush=True)
                yield

        app.router.lifespan_context = combined_lifespan
    except Exception as e:  # pragma: no cover - best-effort registration
        print(f"[server] Failed to set lifespan registration: {e}", flush=True)

    return app


# Export the compiled graph and ASGI app for the server container
graph = create_graph()
app = _build_langgraph_app(graph)
