"""LangGraph server module for the learning agent.

Configures a Postgres checkpointer for persistence so threads and state
survive restarts across container rebuilds. Exposes an ASGI app that serves
the LangGraph API in-process (no external platform/Redis required).
"""

import importlib
import importlib.util
import os
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.graph import END, StateGraph

from learning_agent.agent import create_learning_agent
from learning_agent.config import settings
from learning_agent.providers import get_chat_model
from learning_agent.state import LearningAgentState


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

# Print deepagents module info for sanity at startup
try:  # pragma: no cover - startup diagnostics
    import inspect as _inspect

    import deepagents  # type: ignore
    from deepagents.sub_agent import _create_task_tool as _da_task  # type: ignore

    print("[deepagents] module:", getattr(deepagents, "__file__", None), flush=True)
    _src = _inspect.getsource(_da_task)
    print("[deepagents] task tool contains graph handoff=", ("graph=" in _src), flush=True)
except Exception as _e:  # pragma: no cover - best effort
    print("[deepagents] diagnostics failed:", repr(_e), flush=True)


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
    """Create the LangGraph graph for the learning agent with automatic learning."""
    # Get the base deepagents agent
    from typing import cast

    agent = create_learning_agent()

    # Create a wrapper graph that adds automatic learning submission
    workflow = StateGraph(LearningAgentState)

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

    async def fetch_relevant_learnings_node(state: LearningAgentState) -> LearningAgentState:
        """Enrich the conversation with relevant prior learnings before execution."""

        from learning_agent.learning.langmem_integration import get_learning_system

        messages = list(state.get("messages", []) or [])

        # Find latest human utterance to use as the similarity query
        query: str | None = None
        human_message_count = 0
        last_human_content: str | None = None

        for message in reversed(messages):
            role = getattr(message, "type", None) or getattr(message, "role", None)
            if role == "human":
                content = getattr(message, "content", None)
                if isinstance(content, str) and content.strip():
                    if last_human_content is None:
                        last_human_content = content.strip()
                    human_message_count += 1

        if not last_human_content:
            return state

        # Hybrid approach: First message uses raw content, follow-ups synthesize context
        if human_message_count == 1:
            # First message: use raw content directly
            query = last_human_content
        else:
            # Follow-up message: synthesize task context from conversation history
            try:
                from langchain_core.messages import HumanMessage

                llm = get_chat_model(settings)

                # Build conversation context for synthesis
                conversation_text = []
                for msg in messages[-10:]:  # Last 10 messages for context
                    role = getattr(msg, "type", None) or getattr(msg, "role", None)
                    content = str(getattr(msg, "content", ""))
                    if content and role in ("human", "ai", "assistant"):
                        conversation_text.append(f"{role.upper()}: {content[:200]}")

                synthesis_prompt = f"""Based on this conversation, what is the user trying to accomplish?
Provide a 1-2 sentence task description that captures the overall goal.

Conversation:
{chr(10).join(conversation_text)}

Task description:"""

                synthesis_result = await llm.ainvoke([HumanMessage(content=synthesis_prompt)])
                synthesized = str(getattr(synthesis_result, "content", "")).strip()

                if synthesized:
                    query = synthesized
                    logging.getLogger(__name__).info(f"Synthesized task query: {query[:100]}")
                else:
                    # Fallback to raw message
                    query = last_human_content
            except Exception:
                # Fallback to raw message if synthesis fails
                logging.getLogger(__name__).exception("Failed to synthesize task context")
                query = last_human_content

        if not query:
            return state

        learning_system = get_learning_system()
        try:
            prior = await learning_system.search_similar_tasks(query, limit=3)
        except Exception as exc:  # pragma: no cover - defensive logging only
            logging.getLogger(__name__).exception("Failed to fetch similar learnings", exc_info=exc)
            return state

        if not prior:
            return state

        lines: list[str] = ["Relevant prior learnings from similar tasks:"]
        summaries: list[str] = []
        for item in prior:
            task_name = item.get("similar_task") or item.get("task") or "Unknown task"
            outcome = item.get("outcome") or "unknown"
            confidence = item.get("confidence_score") or 0.0

            parts = [f"Task: {task_name} (outcome: {outcome}, confidence: {confidence:.2f})"]

            for key, label in (
                ("tactical_learning", "Tactical"),
                ("strategic_learning", "Strategic"),
                ("meta_learning", "Meta"),
            ):
                value = (item.get(key) or "").strip()
                if value:
                    parts.append(f"{label}: {value}")

            anti = item.get("anti_patterns") or {}
            anti_parts: list[str] = []
            if isinstance(anti, dict):
                desc = (anti.get("description") or "").strip()
                if desc:
                    anti_parts.append(desc)
                anti_parts.extend(
                    f"Redundancy: {red}" for red in (anti.get("redundancies") or [])[:2]
                )
                anti_parts.extend(
                    f"Inefficiency: {ineff}" for ineff in (anti.get("inefficiencies") or [])[:2]
                )
            if anti_parts:
                parts.append("Anti-patterns: " + "; ".join(anti_parts))

            summary = "\n".join(parts)
            summaries.append(summary)
            lines.append(summary)

        system_message = SystemMessage(content="\n\n".join(lines))
        updated_messages = [*messages, system_message]

        new_state = dict(state)
        new_state["messages"] = updated_messages
        new_state["relevant_learnings"] = summaries
        return new_state  # type: ignore[return-value]

    # Add nodes to the graph
    workflow.add_node("fetch_relevant_learnings", fetch_relevant_learnings_node)
    workflow.add_node("agent", cast("Any", agent))
    workflow.add_node("submit_learning", submit_learning_node)

    # Define the flow
    workflow.set_entry_point("fetch_relevant_learnings")
    workflow.add_edge("fetch_relevant_learnings", "agent")
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
    """Construct the official LangGraph API ASGI app with a default graph.

    This uses the standard create_app factory so the SDK-compatible routes
    like /threads/{thread_id}/runs/stream and /threads/{thread_id}/state work
    without proxy hacks or manual registration.
    """
    # Prefer the official server factory
    mod = _try_import("langgraph_api.server")
    if mod and hasattr(mod, "create_app"):
        create_app = mod.create_app
        try:
            app = create_app(graphs={"learning_agent": graph}, default_graph_id="learning_agent")
            print(
                "[server] Using create_app(graphs=..., default_graph_id=learning_agent)", flush=True
            )
        except TypeError:
            app = create_app(graphs={"learning_agent": graph})
            print("[server] Using create_app(graphs=...)", flush=True)
    else:
        # Fallback: use module.app and register graph on lifespan
        if not mod or not hasattr(mod, "app"):
            raise RuntimeError(
                "langgraph_api.server.create_app not available and module.app missing"
            )
        app = mod.app
        print("[server] Using module.app from langgraph_api.server", flush=True)
        # Register graph during lifespan
        try:
            from contextlib import asynccontextmanager

            import langgraph_api.graph as api_graph  # type: ignore

            original_lifespan = getattr(app.router, "lifespan_context", None)

            @asynccontextmanager
            async def combined_lifespan(a):  # type: ignore
                if original_lifespan:
                    cm = original_lifespan(a)
                else:

                    @asynccontextmanager
                    async def _noop(_):
                        yield

                    cm = _noop(a)
                async with cm:
                    try:
                        await api_graph.register_graph(
                            graph_id="learning_agent", graph=graph, config=None
                        )
                        print(
                            "[server] Registered graph 'learning_agent' with langgraph_api runtime",
                            flush=True,
                        )
                    except Exception as e:
                        print(f"[server] Graph registration failed: {e}", flush=True)
                    try:
                        yield
                    finally:
                        try:
                            from learning_agent.tools.mcp_browser import shutdown_mcp_browser

                            await shutdown_mcp_browser()
                        except Exception as shutdown_exc:
                            print(
                                f"[server] MCP browser shutdown failed: {shutdown_exc}", flush=True
                            )

            app.router.lifespan_context = combined_lifespan
        except Exception as e:
            print(f"[server] Failed to set lifespan registration: {e}", flush=True)

    # Add permissive CORS for local UI/dev usage
    try:
        from starlette.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
        )
    except Exception:
        pass

    # Health endpoint
    try:
        if hasattr(app, "get"):
            app.get("/ok")(lambda: {"status": "ok"})  # type: ignore[misc]
    except Exception:
        pass

    return app


# Export the compiled graph and ASGI app for the server container
graph = create_graph()
app = _build_langgraph_app(graph)
