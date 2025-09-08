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
from learning_agent.agent import create_learning_agent
from learning_agent.config import settings


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
        task_id = progress.add_task("Initializing agent...", total=None)

        try:
            # Initialize agent directly
            agent: Any = create_learning_agent()

            # Create progress callback (unused but kept for compatibility)
            async def update_progress(message: str) -> None:
                progress.update(task_id, description=message)
                # Also print to console for visibility
                console.print(f"[dim]→ {message}[/dim]")

            # Process the task with agent
            console.print(f"\n[bold]Task:[/bold] {task}\n")
            state = {"messages": [{"role": "user", "content": task}]}
            result = await agent.ainvoke(state)

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

    agent: Any = create_learning_agent()

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
                await show_status(agent)
                continue
            if user_input.lower() == "stats":
                show_statistics(agent)
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

                state = {"messages": [{"role": "user", "content": user_input}]}
                result = await agent.ainvoke(state)

            # Display results
            display_results(result)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if settings.debug_mode:
                console.print_exception()


def display_results(result: dict[str, Any]) -> None:
    """Display task execution results."""
    # Try to extract meaningful information from agent result
    status = "success"

    # Check if there's an error in the result
    if "error" in result:
        status = "error"

    # Extract messages if they exist
    messages = result.get("messages", [])

    # Show last message as summary
    summary = ""
    if messages:
        last_msg = messages[-1]
        if hasattr(last_msg, "content"):
            summary = last_msg.content[:500]
        elif isinstance(last_msg, dict) and "content" in last_msg:
            summary = last_msg["content"][:500]

    # Create status panel
    if status == "success":
        status_color = "green"
        status_emoji = "✅"
    else:
        status_color = "red"
        status_emoji = "❌"

    console.print(
        Panel.fit(
            f"{status_emoji} Status: [bold {status_color}]{status.upper()}[/bold {status_color}]",
            title="Execution Summary",
        )
    )

    if summary:
        console.print(f"\n[dim]Result:[/dim]\n{summary}")


async def show_status(agent: Any) -> None:  # noqa: ARG001
    """Show current agent status."""
    # Status method not available on agent directly
    status = {"state": "ready", "tasks_completed": 0}

    table = Table(title="Agent Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("State", str(status.get("state", "Unknown")))
    table.add_row("Tasks Completed", str(status.get("tasks_completed", 0)))

    console.print(table)


def show_statistics(agent: Any) -> None:  # noqa: ARG001
    """Show learning system statistics."""
    # Statistics not directly available on agent
    stats = {"total_memories": 0, "patterns_learned": 0, "success_rate": 0.0}

    table = Table(title="Learning System Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Memories", str(stats.get("total_memories", 0)))
    table.add_row("Recent Memories", str(stats.get("recent_memories", 0)))
    table.add_row("Average Success Rate", f"{stats.get('average_success_rate', 0):.2%}")
    table.add_row("Total Executions", str(stats.get("total_executions", 0)))

    console.print(table)


def show_help() -> None:
    """Show help information."""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]
  help     - Show this help message
  status   - Show current agent status
  stats    - Show learning system statistics
  clear    - Clear the screen
  exit     - Exit the application

[bold cyan]Usage:[/bold cyan]
  Simply type your task or question, and the agent will process it
  using its deep learning capabilities.

[bold cyan]Examples:[/bold cyan]
  • "Refactor the authentication module to use async/await"
  • "Write unit tests for the user service"
  • "Debug the memory leak in the data processor"
"""
    console.print(Panel(help_text, title="Help"))


if __name__ == "__main__":
    app()
