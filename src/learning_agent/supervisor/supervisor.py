"""Supervisor implementation using LangGraph for unified orchestration."""

import uuid
from datetime import datetime
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from learning_agent.config import settings
from learning_agent.learning.narrative_learner import NarrativeLearner
from learning_agent.orchestration import Orchestrator, TodoItem, TodoStatus
from learning_agent.providers import get_chat_model


class TaskPlan(BaseModel):
    """Structured output for task planning."""

    steps: list[str] = Field(
        description="List of concrete action steps to execute. Each step should be a single, actionable command."
    )


class SupervisorState(TypedDict):
    """State for the supervisor graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    task: str
    context: str | None
    todos: list[TodoItem]
    quick_context: dict[str, Any]
    execution_result: dict[str, Any] | None
    current_phase: str
    error: str | None


class Supervisor:
    """
    Supervisor using LangGraph for unified orchestration.

    Manages the entire task lifecycle through a graph-based approach.
    """

    def __init__(self) -> None:
        """Initialize the supervisor with LangGraph."""
        self.config = settings
        self.llm = get_chat_model(self.config)

        # Initialize components
        self.narrative_learner = NarrativeLearner()
        self.orchestrator = Orchestrator()

        # LangGraph checkpointer for resume capabilities
        self.checkpointer = MemorySaver()

        # Build the supervisor graph
        self.graph = self._build_graph()
        self.app = self.graph.compile(checkpointer=self.checkpointer)

        # Track state
        self._background_started = False
        self.current_thread_id: str | None = None

    def _build_graph(self) -> StateGraph[SupervisorState]:
        """Build the LangGraph for supervisor orchestration."""
        workflow = StateGraph(SupervisorState)

        # Add nodes for each phase
        workflow.add_node("check_memory", self._check_memory_node)
        workflow.add_node("plan_task", self._plan_task_node)
        workflow.add_node("execute_todos", self._execute_todos_node)
        workflow.add_node("queue_learning", self._queue_learning_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Define the flow
        workflow.set_entry_point("check_memory")
        workflow.add_edge("check_memory", "plan_task")
        workflow.add_edge("plan_task", "execute_todos")

        # Conditional routing after execution
        workflow.add_conditional_edges(
            "execute_todos",
            lambda state: "handle_error" if state.get("error") else "queue_learning",
            {"queue_learning": "queue_learning", "handle_error": "handle_error"},
        )

        workflow.add_edge("queue_learning", END)
        workflow.add_edge("handle_error", END)

        return workflow

    async def _check_memory_node(self, state: SupervisorState) -> SupervisorState:
        """Node: Check memory for relevant context."""
        state["current_phase"] = "checking_memory"

        # Get quick context from narrative learner
        quick_context = await self.narrative_learner.get_quick_context(state["task"])
        state["quick_context"] = quick_context

        # Add message about memory check
        memory_msg = SystemMessage(
            content=f"Found {len(quick_context.get('recent_memories', []))} relevant memories"
        )
        state["messages"].append(memory_msg)

        return state

    async def _plan_task_node(self, state: SupervisorState) -> SupervisorState:
        """Node: Plan the task execution."""
        state["current_phase"] = "planning"

        # Get todos using structured planning
        todos = await self._plan_with_structure(
            state["task"], state.get("context"), state["quick_context"]
        )
        state["todos"] = todos

        # Add planning message
        plan_msg = SystemMessage(
            content=f"Created {len(todos)} action items: {[t.content for t in todos]}"
        )
        state["messages"].append(plan_msg)

        return state

    async def _execute_todos_node(self, state: SupervisorState) -> SupervisorState:
        """Node: Execute todos through orchestrator."""
        state["current_phase"] = "executing"

        try:
            # Execute through orchestrator (which has its own LangGraph)
            execution_result = await self.orchestrator.orchestrate(state["todos"])
            state["execution_result"] = execution_result

            # Add execution message
            exec_msg = SystemMessage(
                content=f"Executed {len(execution_result['completed'])} todos successfully, "
                f"{len(execution_result['failed'])} failed"
            )
            state["messages"].append(exec_msg)

        except Exception as e:
            state["error"] = str(e)
            error_msg = SystemMessage(content=f"Execution error: {e}")
            state["messages"].append(error_msg)

        return state

    async def _queue_learning_node(self, state: SupervisorState) -> SupervisorState:
        """Node: Queue learning for background processing."""
        state["current_phase"] = "learning"

        if state.get("execution_result"):
            # Queue learning (non-blocking) with callback propagation
            exec_result = state.get("execution_result", {})
            execution_data = {
                "task": state["task"],
                "context": state.get("context"),
                "outcome": "success" if exec_result and exec_result.get("completed") else "failure",
                "duration": 0,  # Will be calculated from timestamps
                "description": self._extract_summary(exec_result) if exec_result else "No result",
                "error": state.get("error"),
            }

            # Pass callbacks as None for now - they will be captured by @traceable decorator
            callbacks = None

            self.narrative_learner.schedule_post_execution_learning(
                execution_data, callbacks=callbacks
            )

            learn_msg = SystemMessage(content="Queued experience for background learning")
            state["messages"].append(learn_msg)

        return state

    async def _handle_error_node(self, state: SupervisorState) -> SupervisorState:
        """Node: Handle errors."""
        state["current_phase"] = "error_handling"

        # Still queue learning from failure
        if state.get("error"):
            execution_data = {
                "task": state["task"],
                "context": state.get("context"),
                "outcome": "failure",
                "duration": 0,
                "description": f"Error: {state['error']}",
                "error": state["error"],
            }
            self.narrative_learner.schedule_post_execution_learning(execution_data)

        return state

    async def process_task(
        self, task: str, context: str | None = None, progress_callback: Any = None
    ) -> dict[str, Any]:
        """
        Process a task through the LangGraph supervisor.

        Args:
            task: The task to accomplish
            context: Additional context about the environment
            progress_callback: Optional callback for progress updates

        Returns:
            Execution result
        """
        # Start background processor on first use
        if not self._background_started:
            await self.narrative_learner.start_background_processor()
            self._background_started = True

        # Create thread ID for checkpoint/resume
        self.current_thread_id = str(uuid.uuid4())

        # Initial state
        initial_state = SupervisorState(
            messages=[HumanMessage(content=task)],
            task=task,
            context=context,
            todos=[],
            quick_context={},
            execution_result=None,
            current_phase="initialization",
            error=None,
        )

        # Configuration with thread ID for checkpointing
        config = {"configurable": {"thread_id": self.current_thread_id}}

        start_time = datetime.now()

        # Run the graph (simpler approach without streaming)
        # Note: progress_callback not used in simplified version
        _ = progress_callback  # Mark as intentionally unused

        # Cast to proper type for LangGraph
        from typing import cast

        final_state = await self.app.ainvoke(cast("Any", initial_state), cast("Any", config))
        state_values = cast("SupervisorState", final_state)

        # Build result from final state
        execution_result = state_values.get("execution_result", {})

        if state_values.get("error"):
            return {
                "status": "error",
                "task": task,
                "error": state_values["error"],
                "duration": (datetime.now() - start_time).total_seconds(),
            }

        if execution_result is None:
            return {
                "status": "failed",
                "task": task,
                "duration": (datetime.now() - start_time).total_seconds(),
                "todos_completed": 0,
                "todos_failed": 0,
                "result": None,
                "summary": "Execution failed",
            }

        return {
            "status": "completed" if execution_result.get("completed") else "failed",
            "task": task,
            "duration": (datetime.now() - start_time).total_seconds(),
            "todos_completed": len(execution_result.get("completed", [])),
            "todos_failed": len(execution_result.get("failed", [])),
            "result": execution_result["completed"][0].result
            if execution_result.get("completed")
            else None,
            "summary": self._extract_summary(execution_result),
        }

    async def _plan_with_structure(
        self, task: str, context: str | None, quick_context: dict[str, Any]
    ) -> list[TodoItem]:
        """
        Planning with proper LLM understanding and memory context.
        Uses structured output to get actionable steps.
        """
        print(f"DEBUG: _plan_with_structure called for: {task}")
        # Get relevant experiences if available
        relevant_experiences = ""
        if quick_context.get("recent_memories"):
            print(f"DEBUG: Found {len(quick_context['recent_memories'])} memories")
            # Just use the most relevant memory directly to avoid extra LLM call
            # The memories are already sorted by relevance from get_quick_context
            relevant_experiences = (
                f"From past experience:\n{quick_context['recent_memories'][0][:500]}..."
            )
            print("DEBUG: Using cached relevant experience")

        # Use LLM with structured output to get actionable steps
        experiences_section = (
            f"Based on my past experiences:\n{relevant_experiences}\n\n"
            if relevant_experiences
            else ""
        )

        planning_prompt = f"""I need to plan how to execute this task:

Task: {task}
Context: {context or "General execution"}

{experiences_section}Create an execution plan. Consider:
- What is the user really asking for?
- What concrete actions must I take?
- Keep each step simple and actionable
- For simple tasks like greetings or calculations, one step is enough
- For complex tasks, break down into necessary steps only

Provide ONLY the actionable steps, not explanations."""

        print("DEBUG: Calling LLM with structured output for planning...")

        # Use structured output with the TaskPlan model
        structured_llm = self.llm.with_structured_output(TaskPlan)
        plan_result: TaskPlan = await structured_llm.ainvoke(planning_prompt)

        print(f"DEBUG: LLM returned {len(plan_result.steps)} structured steps")
        print(f"DEBUG: Steps: {plan_result.steps}")

        # Convert structured steps to TodoItems
        todos = [
            TodoItem(content=step, priority=5, status=TodoStatus.PENDING)
            for step in plan_result.steps
        ]

        # Fallback if no todos (shouldn't happen with structured output)
        if not todos:
            todos.append(TodoItem(content=task, priority=5, status=TodoStatus.PENDING))

        print(f"DEBUG: Created {len(todos)} todos: {[t.content for t in todos]}")
        return todos

    # Removed _plan_from_memory, _is_simple_task, and _parse_quick_plan
    # Now using structured output directly!

    async def resume_task(self, thread_id: str) -> dict[str, Any]:
        """Resume a task from a checkpoint.

        Args:
            thread_id: The thread ID to resume from

        Returns:
            Execution result
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state
        current_state = await self.app.aget_state(config)

        if not current_state or current_state.values is None:
            return {"status": "error", "error": "No checkpoint found for thread ID"}

        # Continue execution from current state
        start_time = datetime.now()

        # Resume the graph execution
        async for _ in self.app.astream_events(None, config, version="v2"):
            pass  # Process events

        # Get final state
        final_state = await self.app.aget_state(config)
        state_values = final_state.values
        execution_result = state_values.get("execution_result", {})

        return {
            "status": "completed" if execution_result.get("completed") else "failed",
            "task": state_values.get("task", "Unknown"),
            "duration": (datetime.now() - start_time).total_seconds(),
            "todos_completed": len(execution_result.get("completed", [])),
            "todos_failed": len(execution_result.get("failed", [])),
            "result": execution_result["completed"][0].result
            if execution_result.get("completed")
            else None,
            "summary": self._extract_summary(execution_result),
        }

    def _extract_summary(self, execution_result: dict[str, Any]) -> str:
        """Extract a summary from execution result."""
        if execution_result.get("completed"):
            # Get the result from the first completed todo
            first_result = execution_result["completed"][0].result
            if first_result and "result" in first_result:
                return str(first_result["result"])[:500]
        elif execution_result.get("error"):
            return f"Error: {execution_result['error']}"
        return "No result available"

    async def shutdown(self) -> None:
        """Shutdown the supervisor."""
        if self._background_started:
            await self.narrative_learner.stop_background_processor()
