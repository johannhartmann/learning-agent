"""CLI entry point for the Learning Agent."""

import asyncio
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table

from learning_agent import __version__
from learning_agent.config import settings
from learning_agent.learning_supervisor import LearningSupervisor


app = typer.Typer(
    name="learning-agent",
    help="A conversational CLI agent that learns from past mistakes and successes.",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"Learning Agent v{__version__}")
        raise typer.Exit()


@app.command()
def main(
    task: str | None = typer.Argument(
        None, help="Task to execute. If not provided, enters interactive mode."
    ),
    config_file: Path | None = typer.Option(  # noqa: ARG001
        None, "--config", "-c", help="Path to configuration file"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
    version: bool = typer.Option(  # noqa: ARG001
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Main entry point for the Learning Agent CLI."""
    if debug:
        settings.debug_mode = True

    if task:
        # Execute single task
        asyncio.run(execute_task(task))
    else:
        # Enter interactive mode
        asyncio.run(interactive_mode())


async def execute_task(task: str) -> None:
    """Execute a single task."""
    console.print(
        Panel.fit(
            f"[bold cyan]Learning Agent[/bold cyan] v{__version__}", subtitle="Executing task..."
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_id = progress.add_task("Initializing supervisor...", total=None)

        try:
            # Initialize supervisor
            supervisor = LearningSupervisor()

            # Create progress callback
            async def update_progress(message: str) -> None:
                progress.update(task_id, description=message)
                # Also print to console for visibility
                console.print(f"[dim]→ {message}[/dim]")

            # Process the task with progress updates
            console.print(f"\n[bold]Task:[/bold] {task}\n")
            result = await supervisor.process_task(task, progress_callback=update_progress)

            # Display results
            display_results(result)

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if settings.debug_mode:
                console.print_exception()


async def interactive_mode() -> None:
    """Run in interactive conversational mode."""
    console.print(
        Panel.fit(
            f"[bold cyan]Learning Agent[/bold cyan] v{__version__}\n"
            "Interactive Mode - Type 'help' for commands or 'exit' to quit",
            title="Welcome",
        )
    )

    supervisor = LearningSupervisor()

    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            # Handle special commands
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            if user_input.lower() == "help":
                show_help()
                continue
            if user_input.lower() == "status":
                await show_status(supervisor)
                continue
            if user_input.lower() == "stats":
                show_statistics(supervisor)
                continue
            if user_input.lower() == "clear":
                console.clear()
                continue

            # Process task
            console.print("\n[bold blue]Agent:[/bold blue] Processing your request...")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Thinking...", total=None)

                result = await supervisor.process_task(user_input)

            # Display results
            display_results(result)

            # Reset for next task - supervisor manages state internally

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if settings.debug_mode:
                console.print_exception()


def display_results(result: dict[str, Any]) -> None:
    """Display task execution results."""
    status = result.get("status", "unknown")

    # Create status panel
    if status == "success":
        status_color = "green"
        status_emoji = "✅"
    elif status == "partial":
        status_color = "yellow"
        status_emoji = "⚠️"
    else:
        status_color = "red"
        status_emoji = "❌"

    # Show execution details if available
    exec_result = result.get("execution_result", {})
    if exec_result:
        completed = exec_result.get("completed", [])
        failed = exec_result.get("failed", [])
        messages = exec_result.get("messages", [])

        # Show completed todos
        if completed:
            console.print(f"\n[green]✓ Completed {len(completed)} task(s):[/green]")
            for todo_id in completed[:5]:  # Show first 5
                console.print(f"  • {todo_id}")

        # Show failed todos
        if failed:
            console.print(f"\n[red]✗ Failed {len(failed)} task(s):[/red]")
            for todo_id in failed[:5]:  # Show first 5
                console.print(f"  • {todo_id}")

        # Show recent messages
        if messages:
            console.print("\n[dim]Recent activity:[/dim]")
            for msg in messages[-3:]:
                console.print(f"  {msg}")

    console.print(
        Panel.fit(
            f"{status_emoji} Status: [bold {status_color}]{status.upper()}[/bold {status_color}]\n"
            f"Duration: {result.get('duration', 0):.2f}s\n"
            f"Tasks: {len(exec_result.get('completed', []))} completed, {len(exec_result.get('failed', []))} failed",
            title="Execution Summary",
        )
    )

    # Show details if available
    details = result.get("details", {})
    if details.get("completed"):
        console.print("\n[green]Completed tasks:[/green]")
        for task in details["completed"]:
            console.print(f"  ✓ {task}")

    if details.get("failed"):
        console.print("\n[red]Failed tasks:[/red]")
        for task, error in details["failed"]:
            console.print(f"  ✗ {task}")
            if error:
                console.print(f"    Error: {error}")


async def show_status(supervisor: LearningSupervisor) -> None:  # noqa: ARG001
    """Show current supervisor status."""
    # Status method not yet implemented
    status = {"state": "ready", "tasks_completed": 0}

    table = Table(title="Supervisor Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Current Task", str(status.get("current_task", "None")))
    table.add_row("Active Todos", str(status.get("active_todos", 0)))
    table.add_row("Pending Todos", str(status.get("pending_todos", 0)))
    table.add_row("Completed Todos", str(status.get("completed_todos", 0)))

    # Add metrics
    metrics = status.get("metrics", {})
    if isinstance(metrics, dict):
        table.add_row("Tasks Completed", str(metrics.get("tasks_completed", 0)))
        table.add_row("Tasks Failed", str(metrics.get("tasks_failed", 0)))
        table.add_row("Memories Stored", str(metrics.get("memories_stored", 0)))

    console.print(table)


def show_statistics(supervisor: LearningSupervisor) -> None:  # noqa: ARG001
    """Show learning system statistics."""
    # Statistics method not yet implemented
    stats = {"total_memories": 0, "patterns_learned": 0, "success_rate": 0.0}

    table = Table(title="Learning System Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Memories", str(stats.get("total_memories", 0)))
    table.add_row("Recent Memories", str(stats.get("recent_memories", 0)))
    table.add_row("Average Success Rate", f"{stats.get('average_success_rate', 0):.2%}")
    table.add_row("Total Executions", str(stats.get("total_executions", 0)))

    console.print(table)

    # Show task type distribution
    distribution: Any = stats.get("task_type_distribution", {})
    if distribution and isinstance(distribution, dict):
        console.print("\n[cyan]Task Type Distribution:[/cyan]")
        for task_type, count in distribution.items():
            console.print(f"  • {task_type}: {count}")


def show_help() -> None:
    """Show help information."""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]
  help     - Show this help message
  status   - Show current supervisor status
  stats    - Show learning system statistics
  clear    - Clear the screen
  exit     - Exit the application

[bold cyan]Usage:[/bold cyan]
  Simply type your task or question, and the agent will decompose it into
  subtasks and execute them in parallel where possible.

[bold cyan]Examples:[/bold cyan]
  • "Refactor the authentication module to use async/await"
  • "Write unit tests for the user service"
  • "Debug the memory leak in the data processor"
"""
    console.print(Panel(help_text, title="Help"))


if __name__ == "__main__":
    app()
