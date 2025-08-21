"""Orchestration layer using LangGraph for parallel task execution."""

import uuid
from datetime import datetime
from typing import Annotated, Any, TypedDict

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from learning_agent.config import settings
from learning_agent.orchestration.models import TodoItem, TodoStatus
from learning_agent.providers import get_chat_model
from learning_agent.tools import FilesystemTool, PlanningTool


class FileNameExtraction(BaseModel):
    """Structured output for extracting filename from request."""

    filename: str = Field(description="The filename or path extracted from the request")


class FileWriteRequest(BaseModel):
    """Structured output for parsing file write requests."""

    filename: str = Field(description="The filename to write to")
    content: str = Field(description="The content to write to the file")


class SearchPattern(BaseModel):
    """Structured output for extracting search patterns."""

    pattern: str = Field(description="The search pattern extracted from the request")


class TaskResponse(BaseModel):
    """Structured output for general task responses."""

    response: str = Field(description="The clear, concise response to the task")


class OrchestratorState(TypedDict):
    """State for the orchestration graph."""

    messages: Annotated[list[Any], add_messages]
    todos: list[TodoItem]
    active_agents: dict[str, str]  # agent_id -> todo_id
    completed_todos: list[str]
    failed_todos: list[str]
    current_phase: str


class Orchestrator:
    """Manages parallel task orchestration using LangGraph."""

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        self.config = settings
        self.checkpointer = MemorySaver()
        # Initialize tools
        self.filesystem_tool = FilesystemTool()
        self.planning_tool = PlanningTool()
        self.llm = get_chat_model(settings)

        # Build the orchestration graph
        self.graph = self._build_graph()
        self.app = self.graph.compile(checkpointer=self.checkpointer)

        # Track active executions
        self.active_executions: dict[str, TodoItem] = {}
        self.execution_results: dict[str, Any] = {}

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph orchestration graph."""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("analyze_dependencies", self.analyze_dependencies)
        workflow.add_node("assign_agents", self.assign_agents)
        workflow.add_node("execute_parallel", self.execute_parallel)
        workflow.add_node("aggregate_results", self.aggregate_results)
        workflow.add_node("handle_failures", self.handle_failures)

        # Add edges
        workflow.set_entry_point("analyze_dependencies")
        workflow.add_edge("analyze_dependencies", "assign_agents")
        workflow.add_edge("assign_agents", "execute_parallel")
        workflow.add_edge("execute_parallel", "aggregate_results")

        # Conditional edges
        workflow.add_conditional_edges(
            "aggregate_results",
            self.check_completion,
            {
                "continue": "assign_agents",
                "handle_failures": "handle_failures",
                "complete": END,
            },
        )

        workflow.add_edge("handle_failures", "assign_agents")

        return workflow

    async def analyze_dependencies(self, state: OrchestratorState) -> OrchestratorState:
        """Analyze todo dependencies and determine execution order."""
        todos = state["todos"]

        # Build dependency graph
        dependency_graph = {}
        for todo in todos:
            dependency_graph[todo.id] = todo.dependencies

        # Find todos that can be executed in parallel (no dependencies or resolved)
        completed = set(state["completed_todos"])
        ready_todos = []

        for todo in todos:
            if todo.status == TodoStatus.PENDING and all(
                dep in completed for dep in todo.dependencies
            ):
                # All dependencies are completed
                ready_todos.append(todo)
                todo.status = TodoStatus.IN_PROGRESS
                todo.started_at = datetime.now()

        state["current_phase"] = "dependency_analysis"
        message = SystemMessage(
            content=f"Analyzed dependencies. {len(ready_todos)} todos ready for execution."
        )
        state["messages"].append(message)

        return state

    async def assign_agents(self, state: OrchestratorState) -> OrchestratorState:
        """Assign todos to available agents."""
        todos = state["todos"]
        active_agents = state.get("active_agents", {})

        # Get todos ready for execution
        ready_todos = [
            todo
            for todo in todos
            if todo.status == TodoStatus.IN_PROGRESS and todo.assigned_agent is None
        ]

        # Limit parallel execution
        max_agents = min(len(ready_todos), self.config.max_parallel_agents)

        # Assign agents to todos
        for _i, todo in enumerate(ready_todos[:max_agents]):
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            todo.assigned_agent = agent_id
            active_agents[agent_id] = todo.id
            self.active_executions[todo.id] = todo

        state["active_agents"] = active_agents
        state["current_phase"] = "agent_assignment"

        message = SystemMessage(content=f"Assigned {len(active_agents)} agents to todos.")
        state["messages"].append(message)

        return state

    async def execute_parallel(self, state: OrchestratorState) -> OrchestratorState:
        """Execute assigned todos in parallel."""
        active_agents = state["active_agents"]
        todos = state["todos"]

        if not active_agents:
            state["current_phase"] = "no_active_agents"
            return state

        # Execute todos in parallel
        import asyncio

        tasks = []
        for agent_id, todo_id in active_agents.items():
            todo = next((t for t in todos if t.id == todo_id), None)
            if todo:
                task = self._execute_single_todo(agent_id, todo)
                tasks.append((todo_id, todo, task))

        # Execute all tasks in parallel
        results = await asyncio.gather(*[t[2] for t in tasks], return_exceptions=True)

        # Process results
        for i, (todo_id, todo, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                todo.status = TodoStatus.FAILED
                todo.error = str(result)
                state["failed_todos"].append(todo_id)
            else:
                todo.status = TodoStatus.COMPLETED
                todo.result = result if isinstance(result, dict) else {"error": str(result)}
                todo.completed_at = datetime.now()
                state["completed_todos"].append(todo_id)

            # Clear assignment
            todo.assigned_agent = None
            if todo_id in self.active_executions:
                del self.active_executions[todo_id]

        # Clear active agents
        state["active_agents"] = {}
        state["current_phase"] = "parallel_execution_complete"

        message = SystemMessage(content=f"Completed parallel execution of {len(results)} todos.")
        state["messages"].append(message)

        return state

    async def _execute_single_todo(self, agent_id: str, todo: TodoItem) -> dict[str, Any]:
        """Execute a single todo item using appropriate tools."""
        try:
            # Parse the todo to determine what tool to use
            result = await self._execute_with_tools(todo)
        except Exception as e:
            return {
                "status": "failed",
                "agent_id": agent_id,
                "todo_id": todo.id,
                "error": str(e),
            }
        else:
            return {
                "status": "completed",
                "agent_id": agent_id,
                "todo_id": todo.id,
                "result": result,
            }

    async def _execute_with_tools(self, todo: TodoItem) -> str:
        """Execute a todo using the appropriate tools."""
        content_lower = todo.content.lower()

        # File operations
        if any(word in content_lower for word in ["count", "list", "files", "directory", "folder"]):
            # List directory contents
            result = self.filesystem_tool._run(action="list_dir", path=".")  # noqa: SLF001
            if "count" in content_lower:
                # Count the files
                files = result.split("\n")
                file_count = len([f for f in files if f.strip()])
                return f"Found {file_count} items in the current directory:\n{result}"
            return result

        if any(word in content_lower for word in ["read", "show", "display", "view"]):
            # Extract filename from todo using structured output
            prompt = f"Extract the filename from this request: {todo.content}"
            structured_llm = self.llm.with_structured_output(FileNameExtraction)
            extraction = await structured_llm.ainvoke(prompt)

            result = self.filesystem_tool._run(action="read", path=extraction.filename)  # noqa: SLF001
            return result

        if any(word in content_lower for word in ["write", "create", "save"]):
            # Parse write request using structured output
            prompt = f"Parse this file write request: {todo.content}"
            structured_llm = self.llm.with_structured_output(FileWriteRequest)
            write_request = await structured_llm.ainvoke(prompt)

            result = self.filesystem_tool._run(  # noqa: SLF001
                action="write", path=write_request.filename, content=write_request.content
            )
            return result

        if any(word in content_lower for word in ["delete", "remove"]):
            # Extract filename from todo using structured output
            prompt = f"Extract the filename/path from this request: {todo.content}"
            structured_llm = self.llm.with_structured_output(FileNameExtraction)
            extraction = await structured_llm.ainvoke(prompt)

            result = self.filesystem_tool._run(action="delete", path=extraction.filename)  # noqa: SLF001
            return result

        if any(word in content_lower for word in ["search", "find"]):
            # Extract search pattern using structured output
            prompt = f"Extract the search pattern from this request: {todo.content}"
            structured_llm = self.llm.with_structured_output(SearchPattern)
            search_request = await structured_llm.ainvoke(prompt)

            result = self.filesystem_tool._run(  # noqa: SLF001
                action="search", path=".", pattern=search_request.pattern
            )
            return result

        # Use LLM for general tasks with structured output
        prompt = f"Complete this task: {todo.content}"
        structured_llm = self.llm.with_structured_output(TaskResponse)
        task_response = await structured_llm.ainvoke(prompt)
        return str(task_response.response)

    async def aggregate_results(self, state: OrchestratorState) -> OrchestratorState:
        """Aggregate results from parallel execution."""
        todos = state["todos"]
        completed = state["completed_todos"]
        failed = state["failed_todos"]

        # Calculate statistics
        total = len(todos)
        completed_count = len(completed)
        failed_count = len(failed)
        pending_count = sum(1 for t in todos if t.status == TodoStatus.PENDING)

        state["current_phase"] = "aggregation"

        message = SystemMessage(
            content=(
                f"Aggregation complete: "
                f"{completed_count}/{total} completed, "
                f"{failed_count} failed, "
                f"{pending_count} pending"
            )
        )
        state["messages"].append(message)

        return state

    def check_completion(self, state: OrchestratorState) -> str:
        """Check if all todos are completed or if we should continue."""
        todos = state["todos"]
        failed = state["failed_todos"]

        # Check if all todos are completed or failed
        all_done = all(todo.status in [TodoStatus.COMPLETED, TodoStatus.FAILED] for todo in todos)

        if all_done:
            return "complete"
        if failed and len(failed) > self.config.max_retries:
            return "handle_failures"
        return "continue"

    async def handle_failures(self, state: OrchestratorState) -> OrchestratorState:
        """Handle failed todos with retry logic."""
        todos = state["todos"]
        failed_todos = state["failed_todos"]

        for todo_id in failed_todos:
            todo = next((t for t in todos if t.id == todo_id), None)
            if todo:
                # Reset status for retry
                todo.status = TodoStatus.PENDING
                todo.error = None

                # Apply learning from failure if available
                # Learning is now handled at supervisor level

        # Clear failed list for retry
        state["failed_todos"] = []
        state["current_phase"] = "retry_preparation"

        message = SystemMessage(content=f"Prepared {len(failed_todos)} todos for retry.")
        state["messages"].append(message)

        return state

    async def orchestrate(self, todos: list[TodoItem]) -> dict[str, Any]:
        """Main orchestration entry point."""
        initial_state = OrchestratorState(
            messages=[],
            todos=todos,
            active_agents={},
            completed_todos=[],
            failed_todos=[],
            current_phase="initialization",
        )

        # Run the orchestration graph
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = await self.app.ainvoke(initial_state, config)

        # Extract results
        results = {
            "completed": [t for t in final_state["todos"] if t.status == TodoStatus.COMPLETED],
            "failed": [t for t in final_state["todos"] if t.status == TodoStatus.FAILED],
            "total_duration": sum(
                (t.completed_at - t.started_at).total_seconds()
                for t in final_state["todos"]
                if t.completed_at and t.started_at
            ),
            "messages": final_state["messages"],
        }

        return results

    def get_execution_state(self) -> dict[str, Any]:
        """Get current execution state."""
        return {
            "active_executions": len(self.active_executions),
            "active_todos": list(self.active_executions.keys()),
            "execution_details": {
                todo_id: {
                    "content": todo.content,
                    "status": todo.status,
                    "assigned_agent": todo.assigned_agent,
                }
                for todo_id, todo in self.active_executions.items()
            },
        }
