"""Planning tool for todo management and task decomposition."""

from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from learning_agent.orchestration.models import TodoItem, TodoStatus


class PlanningInput(BaseModel):
    """Input for planning tool."""

    action: str = Field(description="Action to perform: create, update, delete, list, prioritize")
    content: str | None = Field(None, description="Content for the todo item")
    todo_id: str | None = Field(None, description="ID of todo to update/delete")
    priority: int | None = Field(5, ge=0, le=10, description="Priority level")
    dependencies: list[str] = Field(default_factory=list, description="List of dependency IDs")


class PlanningTool(BaseTool):  # type: ignore[misc]
    """Tool for managing todos and creating execution plans."""

    name: str = "planning_tool"
    description: str = "Create, update, delete, and manage todo items for task execution"
    args_schema: type[BaseModel] = PlanningInput

    def __init__(self) -> None:
        """Initialize the planning tool."""
        super().__init__()
        self._todos: dict[str, TodoItem] = {}
        self._execution_order: list[str] = []

    @property
    def todos(self) -> dict[str, TodoItem]:
        return self._todos

    @property
    def execution_order(self) -> list[str]:
        return self._execution_order

    def _run(self, action: str, **kwargs: Any) -> str:
        """Execute planning action."""
        if action == "create":
            return self._create_todo(**kwargs)
        if action == "update":
            return self._update_todo(**kwargs)
        if action == "delete":
            return self._delete_todo(**kwargs)
        if action == "list":
            return self._list_todos()
        if action == "prioritize":
            return self._prioritize_todos()
        return f"Unknown action: {action}"

    async def _arun(self, action: str, **kwargs: Any) -> str:
        """Async version of run."""
        return self._run(action, **kwargs)

    def _create_todo(
        self,
        content: str,
        priority: int = 5,
        dependencies: list[str] | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> str:
        """Create a new todo item."""
        todo = TodoItem(
            content=content,
            priority=priority,
            dependencies=dependencies or [],
            status=TodoStatus.PENDING,
        )

        self.todos[todo.id] = todo
        return f"Created todo: {todo.id} - {content}"

    def _update_todo(
        self,
        todo_id: str,
        content: str | None = None,
        priority: int | None = None,
        status: str | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> str:
        """Update an existing todo."""
        if todo_id not in self.todos:
            return f"Todo {todo_id} not found"

        todo = self.todos[todo_id]

        if content:
            todo.content = content
        if priority is not None:
            todo.priority = priority
        if status:
            try:
                todo.status = TodoStatus(status)
            except ValueError:
                return f"Invalid status: {status}"

        return f"Updated todo: {todo_id}"

    def _delete_todo(self, todo_id: str, **kwargs: Any) -> str:  # noqa: ARG002
        """Delete a todo item."""
        if todo_id not in self.todos:
            return f"Todo {todo_id} not found"

        del self.todos[todo_id]

        # Remove from dependencies of other todos
        for todo in self.todos.values():
            if todo_id in todo.dependencies:
                todo.dependencies.remove(todo_id)

        return f"Deleted todo: {todo_id}"

    def _list_todos(self, **kwargs: Any) -> str:  # noqa: ARG002
        """List all todos."""
        if not self.todos:
            return "No todos"

        result = "Todos:\n"
        for todo in self.todos.values():
            status_icon = self._get_status_icon(todo.status)
            result += f"{status_icon} [{todo.priority}] {todo.id}: {todo.content}\n"
            if todo.dependencies:
                result += f"   Dependencies: {', '.join(todo.dependencies)}\n"

        return result

    def _prioritize_todos(self, **kwargs: Any) -> str:  # noqa: ARG002
        """Prioritize todos based on dependencies and priority."""
        # Topological sort with priority consideration
        sorted_todos = self._topological_sort()

        if sorted_todos is None:
            return "Error: Circular dependency detected"

        self._execution_order = sorted_todos

        result = "Execution order:\n"
        for i, todo_id in enumerate(sorted_todos, 1):
            todo = self.todos[todo_id]
            result += f"{i}. {todo.content} (priority: {todo.priority})\n"

        return result

    def _topological_sort(self) -> list[str] | None:
        """Perform topological sort on todos."""
        # Build adjacency list
        graph = {todo_id: set(todo.dependencies) for todo_id, todo in self.todos.items()}

        # Find nodes with no dependencies
        no_deps = [todo_id for todo_id, deps in graph.items() if not deps]

        # Sort by priority
        no_deps.sort(key=lambda x: self.todos[x].priority, reverse=True)

        result = []

        while no_deps:
            # Take highest priority todo with no dependencies
            current = no_deps.pop(0)
            result.append(current)

            # Remove current from dependencies of other todos
            for todo_id, deps in graph.items():
                if current in deps:
                    deps.remove(current)
                    if not deps and todo_id not in result:
                        no_deps.append(todo_id)
                        no_deps.sort(key=lambda x: self.todos[x].priority, reverse=True)

        # Check for circular dependencies
        if len(result) != len(self.todos):
            return None

        return result

    def _get_status_icon(self, status: TodoStatus) -> str:
        """Get status icon for display."""
        icons = {
            TodoStatus.PENDING: "⏸",
            TodoStatus.IN_PROGRESS: "🔄",
            TodoStatus.COMPLETED: "✅",
            TodoStatus.FAILED: "❌",
            TodoStatus.BLOCKED: "🚫",
        }
        return icons.get(status, "❓")

    def get_todos(self) -> list[TodoItem]:
        """Get all todos as a list."""
        return list(self.todos.values())

    def get_execution_plan(self) -> dict[str, Any]:
        """Get complete execution plan."""
        sorted_todos = self._topological_sort()

        if sorted_todos is None:
            return {"error": "Circular dependency detected", "todos": self.get_todos()}

        # Group by parallel execution capability
        phases = []
        processed: set[str] = set()

        while len(processed) < len(sorted_todos):
            # Find todos that can run in parallel
            phase = []
            for todo_id in sorted_todos:
                if todo_id in processed:
                    continue

                todo = self.todos[todo_id]
                # Check if all dependencies are processed
                if all(dep in processed for dep in todo.dependencies):
                    phase.append(todo_id)

            if phase:
                phases.append(phase)
                processed.update(phase)
            else:
                # Should not happen with valid topological sort
                break

        return {
            "total_todos": len(self.todos),
            "phases": len(phases),
            "execution_phases": [
                {
                    "phase": i + 1,
                    "parallel_todos": [
                        {
                            "id": todo_id,
                            "content": self.todos[todo_id].content,
                            "priority": self.todos[todo_id].priority,
                        }
                        for todo_id in phase
                    ],
                }
                for i, phase in enumerate(phases)
            ],
        }

    def clear(self) -> None:
        """Clear all todos."""
        self._todos.clear()
        self._execution_order.clear()
