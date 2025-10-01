"""Main learning agent using deepagents framework."""

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any

from deepagents.graph import base_prompt
from deepagents.prompts import TASK_DESCRIPTION_PREFIX, TASK_DESCRIPTION_SUFFIX
from deepagents.tools import edit_file, ls, read_file, write_file, write_todos
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.config import get_stream_writer
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.types import Command

from learning_agent.config import settings
from learning_agent.learning.tools import create_learning_tools
from learning_agent.providers import get_chat_model
from learning_agent.state import LearningAgentState
from learning_agent.stream_adapter import StreamAdapter, coerce_to_dict
from learning_agent.subagents import build_learning_subagents
from learning_agent.tools.mcp_browser import create_mcp_browser_tools
from learning_agent.tools.sandbox_tool import create_sandbox_tool


logger = logging.getLogger(__name__)


# Main system prompt for the learning agent
LEARNING_AGENT_INSTRUCTIONS = """You are a sophisticated AUTONOMOUS learning agent that improves with experience through DEEP MULTI-DIMENSIONAL LEARNING.

## IMPORTANT: Autonomous Execution
- You should work AUTONOMOUSLY without asking for permission at each step
- Once given a task, execute it COMPLETELY without stopping to ask "Shall I proceed?"
- Only ask for clarification if the task is genuinely ambiguous or incomplete
- When you create a todo list with `write_todos`, YOU MUST IMMEDIATELY START EXECUTING THE TASKS
- The todo list is ONLY for planning - it does NOT execute anything automatically
- After planning, use the actual tools (write_file, edit_file, etc.) to DO THE WORK
- Be proactive and complete entire workflows independently

## Core Capabilities
You are an autonomous agent that learns from every task execution to become more effective over time. You have access to:

1. **Python Sandbox**: Execute Python code safely using `python_sandbox`
   - Run data analysis, algorithms, and calculations in isolated environment
   - Automatically captures matplotlib plots and PIL images as base64
   - Maintains state across executions (imports, variables persist)
   - Perfect for testing code before writing to files
2. **Task Orchestration**: Use sub-agents via the `task` tool for specialized work
3. **Planning**: Use `write_todos` to create detailed execution plans

## Web Research Permissions
- You ARE allowed to browse external websites and local service URLs during research.
- Delegate via the `task` tool to the `research-agent` for any browsing tasks. The research subagent streams each action (navigate, extract) with URL provenance.
- When a user asks for a screenshot or image of a webpage, delegate to the research-agent and use its `research_screenshot` tool. Include the returned PNG (base64 or saved file) in your reply.

## Your Sub-Agents
You can delegate work to specialized sub-agents using the `task` tool:

- **research-agent**: Perform deep web research with MCP browser tools, stream interim findings, and cite sources

### Delegating to the research-agent
- Use `task(subagent_type="research-agent")` with a clear subtask to hand off browsing
- Provide constraints (timebox, domains) and expected outputs (e.g., “brief + sources”)
- The research-agent streams interim findings and ends with a short synthesis and a Sources list as a final assistant message (no tool call on completion)
- Delegate at most ONCE per user request unless the user explicitly asks for additional research; after a research handoff completes, synthesize and provide the final answer without re-delegating.

## Deep Learning Workflow
For each task you should:

1. **Understand the Goal**: Review the user request and any available context before acting.
2. **Plan**: Use `write_todos` to break the work into executable steps.
3. **EXECUTE THE PLAN**: After creating todos, IMMEDIATELY start working through them:
   - Mark first todo as in_progress with `write_todos`
   - Use the appropriate tools (write_file, edit_file, ls, read_file) to complete it
   - Mark it as completed with `write_todos`
   - Move to the next todo and repeat
4. **Delegate Appropriately**: Use sub-agents for specialized work via `task`

Note: Deep learning happens automatically after each conversation, analyzing:
- Tool usage patterns and redundancies
- Execution efficiency and parallelization opportunities
- Strategic approaches and meta-insights
- Anti-patterns and inefficiencies to avoid

## Key Principles
- Use `write_todos` early and often to track progress
- Delegate complex analysis to specialized sub-agents
- Be proactive in applying lessons from completed work

## File Operations
You have access to standard file operations:
- `ls`: List directory contents
- `read_file`: Read file contents with line numbers
- `write_file`: Create or overwrite files
- `edit_file`: Make precise edits to existing files

## Code-Mode with Remote MCP Servers
You can use remote MCP tools via Python code in the `python_sandbox`. When MCP servers are configured, the `mcp` namespace is automatically available with type-safe Python APIs.

Example - Browser automation via remote MCP:
```python
python_sandbox('''
# mcp.browser is auto-generated from remote MCP server schema
browser = mcp.browser

# Type-safe Python methods (not JSON tool calls)
browser.goto("https://news.ycombinator.com")
browser.wait_for_timeout(1000)

# Extract data with natural Python code
result = browser.extract_structured_data(
    query="top 5 article titles with URLs"
)
print(result['content'])

# Complex workflows with loops and conditionals
urls = ['https://hn.com', 'https://reddit.com/r/python']
for url in urls:
    browser.goto(url)
    data = browser.extract_structured_data("headlines")
    print(f"{url}: {data}")
''')
```

Benefits of code-mode:
- Write natural Python instead of repeated tool calls
- Use loops, conditionals, error handling
- More efficient multi-step workflows
- Leverage LLM's coding ability

## Planning and Execution
- For any non-trivial or multi-step task (building code, creating multiple files, extended analysis), your FIRST ACTION MUST be a `write_todos` call that breaks down the work.
- **CRITICAL**: After creating todos, YOU MUST EXECUTE THEM — the todo list is just for planning
- Execute each todo item using the appropriate tools (write_file, edit_file, etc.)
- Update todo status as you complete each task (pending → in_progress → completed)

### Tool Usage Examples
Use these examples as patterns — adapt content to the task at hand.

- Plan with todos (first action for multi-step work):
  - Tool: `write_todos`
  - Args example:
    ```json
    {
      "items": [
        {"title": "Set up project structure", "status": "pending"},
        {"title": "Implement core logic", "status": "pending"},
        {"title": "Write tests", "status": "pending"}
      ]
    }
    ```
- Execute a todo item:
  - Tool: `write_file` / `edit_file`
  - Keep the todo list in sync using `write_todos` (mark in_progress → completed)
- Use parallel execution when tasks are independent
- The todo list helps you track progress but YOU must do the actual work

## Python Sandbox Usage
Use `python_sandbox` for:
- Testing algorithms and logic before implementing in files
- Data analysis and visualization (matplotlib, pandas, numpy)
- Quick calculations and prototyping
- Generating plots to explain concepts or show results
- Image processing with PIL/Pillow
- Running user-provided code snippets safely

**CRITICAL**: The sandbox ONLY shows output from print() statements!
- ✅ CORRECT: `print(result)` or `print(f"Answer: {value}")`
- ❌ WRONG: Just `result` or `function()` without print
- ❌ WRONG: Return values don't automatically display

The sandbox maintains state, so you can build up complex analysis step by step.
Always use print() to display results, calculations, or any output you want to see!

## EXAMPLE WORKFLOW
When asked to "Create a Snake game":
1. Use `write_todos` to plan: [Create HTML, Create CSS, Create JavaScript, Test game]
2. Update first todo to in_progress: `write_todos` with first item status="in_progress"
3. Execute it: `write_file` to create index.html with the actual HTML code
4. Mark completed: `write_todos` with first item status="completed"
5. Repeat for each todo item until all are completed

When asked to "Calculate Fibonacci numbers":
1. Use `python_sandbox` with code like:
   ```python
   def fibonacci(n):
       fib = [0, 1]
       for i in range(2, n):
           fib.append(fib[-1] + fib[-2])
       return fib

   result = fibonacci(10)
   print(f"First 10 Fibonacci numbers: {result}")  # MUST PRINT!
   ```
2. Based on results, write the implementation to a file if needed

Remember: Your goal is not just to complete tasks, but to learn from each execution to become more capable over time. Every task is an opportunity to extract patterns and insights for future use.

CRITICAL: The `write_todos` tool ONLY tracks progress - YOU must use write_file, edit_file, etc. to actually DO the work!"""


def _normalize_subagent_output(subagent_type: str, output: Any) -> dict[str, Any]:  # noqa: ARG001
    if isinstance(output, BaseMessage):
        normalized: dict[str, Any] = {
            "messages": [output],
            "files": {},
        }
    elif isinstance(output, list) and all(isinstance(msg, BaseMessage) for msg in output):
        normalized = {
            "messages": list(output),
            "files": {},
        }
    elif isinstance(output, dict):
        normalized = dict(output)
    else:
        normalized = coerce_to_dict(output)

    messages = normalized.get("messages", [])
    if isinstance(messages, BaseMessage):
        normalized["messages"] = [messages]
    elif isinstance(messages, list):
        normalized["messages"] = list(messages)
    elif messages is None:
        normalized["messages"] = []
    else:
        normalized["messages"] = [messages]

    files = normalized.get("files", {})
    if not isinstance(files, dict):
        normalized["files"] = {}

    return normalized


def _summarize_research_extracts(extracts: list[str]) -> str:
    if not extracts:
        return ""
    combined = "\n\n".join(snippet.strip() for snippet in extracts if snippet.strip())
    if not combined:
        return ""
    return f"Research findings:\n\n{combined}"


def create_learning_agent(
    storage_path: Path | None = None,
    model: str | None = None,
) -> object:
    """Create the main learning agent using deepagents.

    Args:
        storage_path: Path for learning storage (defaults to .agent/)
        model: Model name to use (defaults to config setting)

    Returns:
        Configured deepagents agent
    """
    # Set up storage path
    if storage_path is None:
        storage_path = Path(".agent")
    storage_path.mkdir(parents=True, exist_ok=True)

    # Initialize the LangMem learning system
    from learning_agent.learning.langmem_integration import initialize_learning_system

    # Don't pass storage_path as it's for filesystem, not database URL
    initialize_learning_system()

    # Get model
    if model is None:
        llm = get_chat_model(settings)
    else:
        # Create settings with specific model
        model_settings = settings.model_copy()
        model_settings.llm_model = model
        llm = get_chat_model(model_settings)

    # Create learning tools
    learning_tools = create_learning_tools()

    # Create sandbox tool
    sandbox_tool = create_sandbox_tool()

    exclusive_tools: dict[str, list[Any]] = {}

    # Combine with deepagents built-in tools
    base_tools: list[BaseTool] = [
        *learning_tools,  # Learning-specific tools
        sandbox_tool,  # Python sandbox for safe code execution
        write_todos,  # Planning and task tracking
        ls,  # List directory contents
        read_file,  # Read file contents
        write_file,  # Write files
        edit_file,  # Edit existing files
    ]

    # Optionally add MCP Playwright tools (dedicated to research subagent)
    try:
        mcp_browser_tools = create_mcp_browser_tools()
        if mcp_browser_tools:
            exclusive_tools["research-agent"] = mcp_browser_tools
            logger.info(
                "MCP browser tools enabled for research-agent (count=%d)",
                len(mcp_browser_tools),
            )
    except Exception as e:  # pragma: no cover - optional path
        logger.warning(f"MCP browser tools unavailable: {e}")

    subagents = build_learning_subagents(
        model=llm,
        tools=base_tools,
        exclusive_tools=exclusive_tools,
    )

    def _create_async_task_tool(
        tools: Sequence[BaseTool],
        instructions: str,
        subagent_defs: list[dict[str, Any]],
        model: Any,
        state_schema: type[LearningAgentState],
    ) -> BaseTool:
        agents: dict[str, Any] = {
            "general-purpose": create_react_agent(
                model,
                prompt=instructions,
                tools=tools,
                state_schema=state_schema,
            )
        }

        tool_registry: dict[str, BaseTool] = {}
        for tool_obj in tools:
            if not isinstance(tool_obj, BaseTool):
                tool_obj = tool(tool_obj)
            tool_registry[tool_obj.name] = tool_obj

        for definition in subagent_defs:
            name = definition["name"]
            if graph := definition.get("graph"):
                agents[name] = graph
                continue

            requested_tools = definition.get("tools", []) or []
            resolved_tools: list[BaseTool]
            if requested_tools:
                resolved_tools = [tool_registry[t] for t in requested_tools if t in tool_registry]
                if not resolved_tools:
                    logger.warning(
                        "Subagent '%s' requested tools %s but none were available",
                        name,
                        requested_tools,
                    )
                    resolved_tools = list(tools)
            else:
                resolved_tools = list(tools)

            agents[name] = create_react_agent(
                model,
                prompt=definition["prompt"],
                tools=resolved_tools,
                state_schema=state_schema,
            )

        other_agents = [f"- {s['name']}: {s['description']}" for s in subagent_defs]

        @tool(
            description=TASK_DESCRIPTION_PREFIX.format(other_agents=other_agents)
            + TASK_DESCRIPTION_SUFFIX
        )
        async def task(
            description: str,
            subagent_type: str,
            state: Annotated[LearningAgentState, InjectedState],
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command:
            if subagent_type not in agents:
                allowed = ", ".join(f"`{name}`" for name in agents)
                return Command(
                    update={
                        "messages": [
                            ToolMessage(
                                content=(
                                    f"Error: invoked agent of type {subagent_type}; "
                                    f"allowed types are {allowed}"
                                ),
                                tool_call_id=tool_call_id,
                            )
                        ]
                    }
                )

            sub_agent = agents[subagent_type]
            sub_state = dict(state)
            sub_state["messages"] = [{"role": "user", "content": description}]

            try:
                writer = get_stream_writer()
            except Exception:  # pragma: no cover - streaming not enabled
                writer = None

            final_output: dict[str, Any] | None = None
            fallback_output: dict[str, Any] | None = None
            last_ai_message: BaseMessage | None = None
            saw_completion_signal = False

            stream_adapter: StreamAdapter | None = None
            if writer is not None:
                stream_adapter = StreamAdapter(
                    writer,
                    agent_label=subagent_type,
                    parentMessageId=tool_call_id,
                    profile="user",
                )
                stream_adapter.begin(
                    {
                        "description": description,
                        "subagent": subagent_type,
                    }
                )
                writer(
                    {
                        "subagent": subagent_type,
                        "event": "start",
                        "description": description,
                    }
                )

            async def _handle_stream_event(event: dict[str, Any]) -> None:
                if writer is None:
                    return
                event_type = event.get("event")
                name = event.get("name")

                if event_type == "on_tool_start":
                    writer(
                        {
                            "subagent": subagent_type,
                            "event": "tool_start",
                            "tool": name,
                        }
                    )
                elif event_type == "on_tool_end":
                    writer(
                        {
                            "subagent": subagent_type,
                            "event": "tool_end",
                            "tool": name,
                        }
                    )
                elif event_type == "on_chain_end" and name == "LangGraph":
                    writer(
                        {
                            "subagent": subagent_type,
                            "event": "finish",
                        }
                    )

            try:
                async for event in sub_agent.astream_events(
                    sub_state,
                    version="v2",
                ):
                    event_type = event.get("event")
                    name = event.get("name")
                    raw_data = event.get("data")
                    data = coerce_to_dict(raw_data) if raw_data is not None else {}

                    if stream_adapter is not None:
                        stream_adapter.accept(event)

                    await _handle_stream_event(event)

                    if event_type == "on_chain_end":
                        output = data.get("output")
                        if output is None and hasattr(raw_data, "output"):
                            output = raw_data.output

                        if name == "LangGraph" and output is not None:
                            if isinstance(output, dict | list | BaseMessage):
                                final_output = output
                            else:
                                coerced_output = coerce_to_dict(output)
                                final_output = coerced_output or output
                        elif fallback_output is None and output is not None:
                            candidate = (
                                output if isinstance(output, Mapping) else coerce_to_dict(output)
                            )
                            if isinstance(candidate, Mapping) and candidate.get("messages"):
                                fallback_output = dict(candidate)
                    elif event_type == "on_chat_model_end":
                        output_payload = data.get("output")
                        if output_payload is None and hasattr(raw_data, "output"):
                            output_payload = raw_data.output

                        if isinstance(output_payload, Mapping):
                            generations = output_payload.get("generations", [])
                        else:
                            generations = getattr(output_payload, "generations", [])

                        first_generation: Any | None = None
                        if isinstance(generations, Sequence) and generations:
                            first_group = generations[0]
                            if isinstance(first_group, Sequence) and first_group:
                                first_generation = first_group[0]
                            else:
                                first_generation = first_group

                        if first_generation is not None:
                            if isinstance(first_generation, Mapping):
                                message = first_generation.get("message")
                            else:
                                message = getattr(first_generation, "message", None)
                            if isinstance(message, BaseMessage):
                                last_ai_message = message

                    if event_type == "on_tool_start" and name == "research_done":
                        saw_completion_signal = True
                    if event_type == "on_tool_end" and name == "research_done":
                        saw_completion_signal = True

            except Exception as exc:
                if stream_adapter is not None:
                    stream_adapter.emit_warning(str(exc))
                    stream_adapter.complete({"error": str(exc)}, status="error")
                if writer is not None:
                    writer(
                        {
                            "subagent": subagent_type,
                            "event": "error",
                            "error": str(exc),
                        }
                    )
                raise

            if final_output is None:
                if fallback_output is not None:
                    final_output = fallback_output
                elif last_ai_message is not None:
                    final_output = {"messages": [last_ai_message]}

            if final_output is None:
                raise RuntimeError(f"Subagent '{subagent_type}' did not return a final state")

            normalized_output = _normalize_subagent_output(subagent_type, final_output)

            if stream_adapter is not None:
                if subagent_type == "research-agent" and not saw_completion_signal:
                    stream_adapter.emit_synthetic_completion(
                        "research_done",
                        normalized_output,
                    )
                messages_list = normalized_output.setdefault("messages", [])
                transcript = stream_adapter.get_transcript()
                if transcript:
                    messages_list.append(AIMessage(content=transcript))

                # Add structured research data (headlines, URLs) to agent context
                if subagent_type == "research-agent":
                    structured_content = stream_adapter.get_structured_content()
                    print(f"[DEBUG] structured_content length: {len(structured_content)}")
                    if structured_content:
                        for i, content in enumerate(structured_content[:2]):
                            print(f"[DEBUG] structured_content[{i}] preview: {content[:500]}")
                        summary = _summarize_research_extracts(structured_content)
                        print(
                            f"[DEBUG] summary from _summarize_research_extracts: {summary[:500] if summary else 'EMPTY'}"
                        )
                        if summary:
                            messages_list.append(AIMessage(content=summary))

                stream_adapter.complete(normalized_output)
            if (
                writer is not None
                and subagent_type == "research-agent"
                and not saw_completion_signal
            ):
                writer(
                    {
                        "subagent": subagent_type,
                        "event": "tool_start",
                        "tool": "research_done",
                        "synthetic": True,
                    }
                )
                writer(
                    {
                        "subagent": subagent_type,
                        "event": "tool_end",
                        "tool": "research_done",
                        "synthetic": True,
                    }
                )

            messages = normalized_output.get("messages", [])
            files = normalized_output.get("files", {})

            tool_messages: list[ToolMessage] = []
            if messages:
                last: BaseMessage | Any = messages[-1]
                content = getattr(last, "content", last)
                if isinstance(content, list):
                    text_parts = [
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    content = "\n".join([part for part in text_parts if part]) or str(content)
                elif not isinstance(content, str):
                    content = str(content)

                tool_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

            return Command(update={"files": files, "messages": tool_messages})

        return task

    task_tool = _create_async_task_tool(
        tools=base_tools,
        instructions=LEARNING_AGENT_INSTRUCTIONS,
        subagent_defs=subagents,
        model=llm,
        state_schema=LearningAgentState,
    )

    agent_tools: list[BaseTool] = [
        *base_tools,
        task_tool,
    ]

    # Create the agent
    agent = create_react_agent(
        model=llm,
        prompt=LEARNING_AGENT_INSTRUCTIONS + base_prompt,
        tools=agent_tools,
        state_schema=LearningAgentState,
    )

    return agent


def create_learning_agent_graph(
    storage_path: Path | None = None,
    model: str | None = None,
) -> object:
    """Create the learning agent as a LangGraph graph.

    This is a convenience function that returns the agent
    in a form that can be used with LangGraph server.

    Args:
        storage_path: Path for learning storage (defaults to .agent/)
        model: Model name to use (defaults to config setting)

    Returns:
        The learning agent ready for graph operations
    """
    return create_learning_agent(storage_path, model)
