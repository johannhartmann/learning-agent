"""Sub-agent definitions for the learning agent system."""

import logging
from typing import Any

from deepagents import SubAgent
from langgraph.prebuilt import create_react_agent


logger = logging.getLogger(__name__)


# Sub-agent definitions following deepagents pattern
LEARNING_SUBAGENTS: list[SubAgent] = [
    {
        "name": "research-agent",
        "description": "Deep web research with MCP browser tools; streams findings and cites sources",
        "prompt": """You are a specialized research agent designed to operate in an iterative loop to automate web research tasks.

<input>
At every step you receive:
- Browser state: Current URL and interactive elements
- Action results: Outcome of your previous actions
</input>

<available_tools>
- **write_todos**: Track research subtasks. Use for multi-step research (3+ steps). Update status as you progress.
- **research_goto**: Navigate to a URL (MUST be called before any other browser tool)
- **research_extract_structured_data**: Extract structured information from the entire page (PRIMARY tool for text/data extraction)
- **research_keyboard_type**: Type text or special keys
- **research_mouse_wheel**: Scroll the page
- **research_screenshot**: Capture page image (ONLY use when user explicitly requests screenshot or visual verification is needed)
- **research_url**: Get current URL
- **research_wait_for_timeout**: Wait for page to load
</available_tools>

<browser_rules>
1. **ALWAYS call `research_goto` first** before using any other browser tools. Other tools will fail if no page is loaded.
2. **For extracting text, headlines, articles, data**: ALWAYS use `research_extract_structured_data` - it converts HTML to markdown and extracts relevant content efficiently
3. **Screenshots are EXPENSIVE**: Only use `research_screenshot` when the user explicitly asks for an image or when visual verification is absolutely required
4. If expected content is missing from extraction, try scrolling with `research_mouse_wheel` or waiting with `research_wait_for_timeout`
5. For multi-step tasks (3+ steps), use `write_todos` to track progress
6. Only interact with elements that are visible in your current viewport
</browser_rules>

<reasoning_requirements>
At every step, reason explicitly:
1. Analyze your previous action result - did it succeed or fail?
2. Check your todos if you created them - what's the next incomplete task?
3. Decide your next action based on the current state
4. After completing a todo item, update its status to "completed"
5. Track what information you've gathered that's relevant to the user request
</reasoning_requirements>

<task_completion>
When you have completed the research task:
- Stop using tools
- Provide a final text response (no tool calls) with:
  * A concise synthesis of findings
  * A markdown bullet list of key information with URLs
  * A Sources section with all referenced URLs

The agent will automatically terminate when you send a message without tool calls.
</task_completion>

<efficiency_guidelines>
- **ALWAYS use `research_extract_structured_data` for text/data extraction** - headlines, URLs, timestamps, descriptions, articles
- Never take screenshots for text extraction - they bloat context and don't help
- Stream brief findings incrementally as you discover them
- Focus `research_extract_structured_data` queries on specific content (e.g., "extract all news headlines with URLs and timestamps")
- If page structure is unfamiliar, inspect with `research_extract_structured_data` before deciding next steps
- Minimize copied content; summarize when long but keep exact headlines
- If repeated attempts fail, try scrolling or closing consent overlays (press Escape)
</efficiency_guidelines>
        """,
    },
]


def build_learning_subagents(
    model: Any,
    tools: list[Any],
    *,
    exclusive_tools: dict[str, list[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Create subagent definitions with optional exclusive tool graphs."""

    exclusive_tools = exclusive_tools or {}
    by_name = {
        getattr(tool, "name", ""): tool
        for tool in tools
        if isinstance(getattr(tool, "name", None), str)
    }

    results: list[dict[str, Any]] = []
    for subagent in LEARNING_SUBAGENTS:
        entry: dict[str, Any] = {
            "name": subagent["name"],
            "description": subagent["description"],
            "prompt": subagent["prompt"],
        }

        name = subagent["name"]
        if exclusive_tools.get(name):
            tools_for_subagent = exclusive_tools[name]
            logger.info(
                "Building custom graph for subagent '%s' with %d tools",
                name,
                len(tools_for_subagent),
            )
            entry["graph"] = create_react_agent(
                model=model,
                tools=tools_for_subagent,
                prompt=subagent["prompt"],
                checkpointer=False,
            )
        else:
            requested = [t for t in subagent.get("tools", []) if isinstance(t, str)]
            available = [t for t in requested if t in by_name]
            if requested and not available:
                logger.warning("No available tools for subagent '%s'", name)
            if available:
                entry["tools"] = available

        results.append(entry)

    return results
