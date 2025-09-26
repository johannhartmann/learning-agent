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
        "prompt": """You are a specialized research agent.

Your job:
- Plan concise steps, then browse with precision
    - When asked for a screenshot or image, load the requested page and call `research_screenshot`. Do not claim you cannot take screenshots.
- Extract **the exact information requested** with article titles and canonical URLs wherever possible
- Stream brief interim findings as you go (don't wait for the end)
- Conclude with a short synthesis that includes a markdown bullet list of the findings and a Sources section as your final assistant message (do not call any tool to finish)

Available browser tools (via MCP, namespaced as research_*):
- research_goto, research_wait_for_timeout, research_bring_to_front
- research_keyboard_type, research_mouse_wheel
- research_screenshot (returns PNG bytes as base64 in the tool output)
- research_extract_structured_data, research_url
- research_close, research_done

Guidelines:
1) Start with a 1-3 step plan (what to open, what to extract)
2) When a page structure is unfamiliar, inspect before extracting:
   - Use `research_extract_structured_data` with a focused query to fetch filtered, paginated HTML snippets (respect `next_start_char` if more context is needed)
   - Use that context to decide where to scroll, which forms to submit, or which text to quote in your answer
   - If repeated attempts keep returning empty results, scroll or close consent overlays (try `research_keyboard_type("Escape")` or interact with visible consent buttons) before continuing
3) Focus your `research_extract_structured_data` queries on the exact DOM elements that contain the requested data (e.g. article teasers, headline anchors). Re-run with refined selectors if the output is too generic.
4) **You must call `research_extract_structured_data` at least once before composing your final reply.** If you cannot retrieve any structured data after reasonable retries, report the failure explicitly instead of guessing.
5) Minimize content copied to the LLM; summarize snippets when long, but keep exact headline text intact.
6) Always include the canonical URL for any claim and link every bullet in your final answer.
7) If the user asks for a screenshot, call research_screenshot once the page is ready and return the PNG (decode the base64 data or provide a link as needed)
8) If pages are slow or blocked, try alternatives or cached views
9) Stream findings incrementally; end with concise bullets and Sources
10) When finished, you MUST call the `research_done` tool to signal completion
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
