# Deep Agents Usage Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Creating a Deep Agent](#creating-a-deep-agent)
6. [Sub-Agents](#sub-agents)
7. [File System Tools](#file-system-tools)
8. [Planning and Task Management](#planning-and-task-management)
9. [Human-in-the-Loop](#human-in-the-loop)
10. [Advanced Configuration](#advanced-configuration)
11. [Async Agents](#async-agents)
12. [MCP Integration](#mcp-integration)
13. [Best Practices](#best-practices)
14. [Common Patterns](#common-patterns)
15. [Troubleshooting](#troubleshooting)

## Introduction

`deepagents` is a Python library that creates powerful, multi-layered AI agents capable of handling complex, long-running tasks. It builds upon LangGraph to provide agents with:

- **Hierarchical task decomposition** through sub-agents
- **Built-in planning capabilities** via a todo management system
- **Virtual file system** for managing intermediate outputs
- **Human-in-the-loop** approval workflows
- **Context quarantine** to prevent context pollution

The library was inspired by advanced AI systems like Claude Code, Deep Research, and Manus, abstracting their core patterns into a reusable framework.

## Core Concepts

### What Makes an Agent "Deep"?

Traditional loop-based agents struggle with complex, multi-step tasks. Deep agents overcome this through:

1. **Planning Tool**: Explicit task planning and tracking
2. **Sub-Agents**: Specialized agents for context isolation and focused tasks
3. **File System**: Persistent storage for intermediate work products
4. **Detailed Prompting**: Comprehensive system prompts guiding agent behavior

### Key Components

- **Main Agent**: The orchestrator that manages the overall task
- **Sub-Agents**: Specialized workers for specific subtasks
- **State Management**: LangGraph state tracking todos, files, and messages
- **Built-in Tools**: File operations, planning, and sub-agent invocation

## Quick Start

### Installation

```bash
pip install deepagents
```

### Basic Example

```python
from deepagents import create_deep_agent

# Define a tool
def analyze_data(data: str):
    """Analyze provided data"""
    return f"Analysis of: {data}"

# Create the agent
agent = create_deep_agent(
    tools=[analyze_data],
    instructions="You are a data analyst expert."
)

# Run the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze sales trends"}]
})
```

## Architecture

### State Schema

Deep agents use an extended LangGraph state:

```python
class DeepAgentState(AgentState):
    todos: NotRequired[list[Todo]]  # Task tracking
    files: NotRequired[dict[str, str]]  # Virtual filesystem
```

### Message Flow

1. User provides input message
2. Main agent processes with access to tools and planning
3. Can delegate to sub-agents for specialized work
4. Sub-agent results merge back into main state
5. Final response returned to user

## Creating a Deep Agent

### Required Parameters

```python
agent = create_deep_agent(
    tools=[...],           # List of tools/functions
    instructions="..."     # Agent-specific prompt prefix
)
```

### Optional Parameters

```python
agent = create_deep_agent(
    tools=[...],
    instructions="...",
    model="claude-3-sonnet",           # Custom model
    subagents=[...],                   # Custom sub-agents
    builtin_tools=["write_todos"],     # Limit built-in tools
    interrupt_config={...},             # Human approval config
    state_schema=CustomState,           # Custom state class
    main_agent_tools=["tool1"]          # Limit main agent tools
)
```

### Tool Definition

Tools can be:
- Plain Python functions
- Functions decorated with `@tool`
- LangChain `BaseTool` instances

```python
# Plain function
def search(query: str):
    return f"Results for {query}"

# Decorated function
from langchain_core.tools import tool

@tool
def search(query: str):
    """Search the web"""
    return f"Results for {query}"

# Pass to agent
agent = create_deep_agent([search], "...")
```

## Sub-Agents

### Why Sub-Agents?

Sub-agents provide:
- **Context Quarantine**: Isolate complex explorations
- **Specialization**: Different prompts/tools for specific tasks
- **Parallelization**: Run multiple sub-tasks concurrently
- **Model Flexibility**: Use different models per sub-agent

### Defining Sub-Agents

#### Standard Sub-Agent

```python
research_agent = {
    "name": "researcher",
    "description": "Conducts in-depth research",
    "prompt": "You are an expert researcher...",
    "tools": ["search", "read_file"],  # Optional: subset of tools
    "model": {  # Optional: override model
        "model": "gpt-4",
        "temperature": 0.7
    }
}

agent = create_deep_agent(
    tools=[search, read_file, write_file],
    instructions="...",
    subagents=[research_agent]
)
```

#### Custom Graph Sub-Agent

```python
from langgraph.prebuilt import create_react_agent

# Create custom agent graph
custom_graph = create_react_agent(
    model=specialized_model,
    tools=specialized_tools,
    prompt="Specialized prompt..."
)

custom_subagent = {
    "name": "analyzer",
    "description": "Analyzes complex data",
    "graph": custom_graph  # Pre-built graph
}

agent = create_deep_agent(
    tools=[...],
    instructions="...",
    subagents=[custom_subagent]
)
```

### General-Purpose Sub-Agent

Every deep agent has a built-in `general-purpose` sub-agent that:
- Uses the same instructions as the main agent
- Has access to all tools
- Useful for delegating without specialization

## File System Tools

### Virtual File System

Deep agents include a virtual file system for managing work products:

```python
# Pass initial files
result = agent.invoke({
    "messages": [...],
    "files": {
        "data.txt": "Initial data",
        "config.json": '{"setting": "value"}'
    }
})

# Retrieve modified files
final_files = result["files"]
```

### Built-in File Operations

#### List Files (`ls`)
```python
# Returns list of file names
files = ls()  # ['data.txt', 'report.md']
```

#### Read File (`read_file`)
```python
# Read with line numbers (cat -n format)
content = read_file(
    file_path="data.txt",
    offset=0,      # Start line (optional)
    limit=2000     # Max lines (optional)
)
```

#### Write File (`write_file`)
```python
# Create or overwrite file
write_file(
    file_path="output.txt",
    content="File contents"
)
```

#### Edit File (`edit_file`)
```python
# Replace specific strings
edit_file(
    file_path="code.py",
    old_string="def old_function():",
    new_string="def new_function():",
    replace_all=False  # Only first occurrence
)
```

### File System Limitations

- **Single level**: No subdirectories currently
- **In-memory**: Files exist only during agent execution
- **State-based**: Files stored in LangGraph state

## Planning and Task Management

### Todo Tool

The `write_todos` tool helps agents plan and track complex tasks:

```python
todos = [
    {
        "content": "Research the topic",
        "status": "pending"  # or "in_progress", "completed"
    },
    {
        "content": "Write first draft",
        "status": "pending"
    }
]
```

### When Planning is Used

The built-in prompting encourages todo usage for:
- Tasks with 3+ steps
- Complex multi-part requests
- User-provided task lists
- Tasks needing progress tracking

### Planning Best Practices

1. **Break down complex tasks** into manageable steps
2. **Update status** as work progresses
3. **Add new todos** as discoveries are made
4. **Remove obsolete items** to keep list relevant

## Human-in-the-Loop

### Configuration

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_deep_agent(
    tools=[sensitive_tool, safe_tool],
    instructions="...",
    interrupt_config={
        "sensitive_tool": {
            "allow_accept": True,
            "allow_edit": True,
            "allow_respond": True,
            "allow_ignore": False  # Not supported yet
        },
        "safe_tool": False  # No interrupt
    }
)

# Attach checkpointer (required for interrupts)
agent.checkpointer = InMemorySaver()
```

### Interrupt Workflows

#### Accept Tool Call

```python
config = {"configurable": {"thread_id": "1"}}

# Stream until interrupt
for chunk in agent.stream({"messages": [...]}, config):
    print(chunk)

# Accept the tool call
from langgraph.types import Command
for chunk in agent.stream(
    Command(resume=[{"type": "accept"}]),
    config
):
    print(chunk)
```

#### Edit Tool Call

```python
# Edit tool name and/or arguments
for chunk in agent.stream(
    Command(resume=[{
        "type": "edit",
        "args": {
            "action": "different_tool",
            "args": {"param": "new_value"}
        }
    }]),
    config
):
    print(chunk)
```

#### Respond Instead of Calling

```python
# Provide response without calling tool
for chunk in agent.stream(
    Command(resume=[{
        "type": "response",
        "args": "Manual response text"
    }]),
    config
):
    print(chunk)
```

## Advanced Configuration

### Custom Models

```python
from langchain.chat_models import init_chat_model

# Use any LangChain-compatible model
model = init_chat_model("openai:gpt-4")

agent = create_deep_agent(
    tools=[...],
    instructions="...",
    model=model
)
```

### Per-Subagent Models

```python
subagents = [
    {
        "name": "fast-analyzer",
        "description": "Quick analysis",
        "prompt": "Analyze quickly",
        "model": {
            "model": "claude-3-haiku",
            "temperature": 0,
            "max_tokens": 4096
        }
    },
    {
        "name": "deep-thinker",
        "description": "Complex reasoning",
        "prompt": "Think deeply",
        "model": {
            "model": "claude-3-opus",
            "temperature": 0.7
        }
    }
]
```

### Custom State Schema

```python
from deepagents import DeepAgentState

class CustomState(DeepAgentState):
    custom_field: str
    metrics: dict[str, float]

agent = create_deep_agent(
    tools=[...],
    instructions="...",
    state_schema=CustomState
)
```

### Limiting Built-in Tools

```python
# Only enable specific built-in tools
agent = create_deep_agent(
    tools=[...],
    instructions="...",
    builtin_tools=["write_todos", "read_file"]
    # Excludes: write_file, edit_file, ls
)
```

## Async Agents

### Creating Async Agents

```python
from deepagents import async_create_deep_agent
import asyncio

async def async_tool(query: str):
    await asyncio.sleep(1)
    return f"Async result: {query}"

agent = async_create_deep_agent(
    tools=[async_tool],
    instructions="..."
)

# Run async
async def main():
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": "..."}]
    })

asyncio.run(main())
```

### Streaming Async Responses

```python
async def stream_agent():
    async for chunk in agent.astream(
        {"messages": [...]},
        stream_mode="values"
    ):
        if "messages" in chunk:
            print(chunk["messages"][-1].content)
```

## MCP Integration

### Using MCP Tools

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import async_create_deep_agent

async def setup_mcp_agent():
    # Get MCP tools
    mcp_client = MultiServerMCPClient(...)
    mcp_tools = await mcp_client.get_tools()

    # Create agent with MCP tools
    agent = async_create_deep_agent(
        tools=mcp_tools,
        instructions="Use MCP tools to..."
    )

    return agent
```

## Best Practices

### 1. Prompt Engineering

```python
instructions = """You are an expert {domain} specialist.

Key responsibilities:
- {responsibility_1}
- {responsibility_2}

Guidelines:
- Always verify data before processing
- Document your reasoning in files
- Break complex tasks into subtasks

Output format: {format_spec}
"""
```

### 2. Tool Design

```python
def good_tool(
    param: str,
    optional: int = 5
) -> dict:
    """Clear description of what tool does.

    Args:
        param: What this parameter controls
        optional: Optional parameter with default

    Returns:
        Structured output with clear schema
    """
    # Validate inputs
    if not param:
        raise ValueError("param is required")

    # Process
    result = process(param, optional)

    # Return structured data
    return {
        "status": "success",
        "data": result
    }
```

### 3. Sub-Agent Specialization

```python
subagents = [
    # Research specialist
    {
        "name": "researcher",
        "description": "Gathers and synthesizes information",
        "prompt": research_prompt,
        "tools": ["search", "read_file"]
    },
    # Analysis specialist
    {
        "name": "analyzer",
        "description": "Performs deep analysis",
        "prompt": analysis_prompt,
        "tools": ["calculate", "visualize"]
    },
    # Critique specialist
    {
        "name": "critic",
        "description": "Reviews and improves outputs",
        "prompt": critique_prompt,
        "tools": ["read_file", "edit_file"]
    }
]
```

### 4. State Management

```python
# Initialize with context
initial_state = {
    "messages": [{"role": "user", "content": "..."}],
    "files": {
        "context.md": "Background information",
        "requirements.txt": "Project requirements"
    }
}

# Process
result = agent.invoke(initial_state)

# Extract results
output_files = result["files"]
final_report = output_files.get("report.md", "")
```

## Common Patterns

### Research Agent Pattern

```python
research_instructions = """You are an expert researcher.

Process:
1. Write the research question to question.txt
2. Use researcher sub-agent for deep dives
3. Synthesize findings in report.md
4. Use critic sub-agent for review
5. Iterate until satisfied

Always cite sources and verify facts.
"""

research_subagent = {
    "name": "researcher",
    "description": "Conducts focused research",
    "prompt": "Research thoroughly and return findings"
}

critic_subagent = {
    "name": "critic",
    "description": "Reviews research quality",
    "prompt": "Critique for accuracy and completeness"
}

agent = create_deep_agent(
    tools=[web_search, extract_content],
    instructions=research_instructions,
    subagents=[research_subagent, critic_subagent]
)
```

### Code Generation Pattern

```python
coding_instructions = """You are an expert programmer.

Workflow:
1. Understand requirements
2. Plan implementation with todos
3. Write code to appropriate files
4. Add tests
5. Document in README.md

Follow language best practices and conventions.
"""

agent = create_deep_agent(
    tools=[code_analyzer, test_runner],
    instructions=coding_instructions,
    builtin_tools=["write_todos", "write_file", "edit_file", "read_file", "ls"]
)
```

### Analysis Pipeline Pattern

```python
pipeline_instructions = """You are a data analysis pipeline.

Steps:
1. Load data from input files
2. Clean and preprocess
3. Run analysis with analyzer sub-agent
4. Generate visualizations
5. Write findings to report.md

Maintain data lineage and document transformations.
"""

analyzer_subagent = {
    "name": "analyzer",
    "description": "Performs statistical analysis",
    "prompt": "Analyze data thoroughly",
    "model": {"model": "gpt-4", "temperature": 0}
}

agent = create_deep_agent(
    tools=[load_data, transform, visualize],
    instructions=pipeline_instructions,
    subagents=[analyzer_subagent]
)
```

## Troubleshooting

### Common Issues

#### 1. Sub-agent Not Found

```python
# Error: "invoked agent of type X, only allowed types are..."

# Solution: Ensure sub-agent name matches exactly
subagents = [
    {"name": "researcher", ...}  # Must use "researcher" not "research"
]
```

#### 2. Interrupt Without Checkpointer

```python
# Error: Interrupts fail silently

# Solution: Attach checkpointer
from langgraph.checkpoint.memory import InMemorySaver
agent.checkpointer = InMemorySaver()
```

#### 3. File Not Found

```python
# Error: "File 'X' not found"

# Solution: Check file was created or passed in initial state
initial_state = {
    "messages": [...],
    "files": {"required_file.txt": "content"}
}
```

#### 4. Tool Not Available to Sub-agent

```python
# Sub-agent can't access tool

# Solution: Don't restrict tools or include in list
subagent = {
    "name": "worker",
    "tools": ["needed_tool"],  # Explicitly include
    # Or omit "tools" to give access to all
}
```

### Performance Optimization

#### 1. Minimize Context Size

```python
# Use sub-agents for exploration
research_subagent = {
    "name": "researcher",
    "description": "Research specific topics",
    "prompt": "Return only essential findings"
}
```

#### 2. Parallel Sub-agent Calls

```python
# Main agent can invoke multiple sub-agents simultaneously
# The system handles parallelization automatically
```

#### 3. Limit File Sizes

```python
# Read files in chunks
content = read_file("large.txt", offset=0, limit=1000)
```

#### 4. Optimize Model Selection

```python
# Use faster models for simple tasks
subagents = [
    {
        "name": "quick-check",
        "model": {"model": "claude-3-haiku"},
        ...
    }
]
```

### Debugging Tips

#### 1. Enable Streaming

```python
for chunk in agent.stream({"messages": [...]}, stream_mode="values"):
    if "messages" in chunk:
        print(f"Agent: {chunk['messages'][-1].content}")
    if "todos" in chunk:
        print(f"Todos: {chunk['todos']}")
```

#### 2. Inspect State

```python
result = agent.invoke({"messages": [...]})
print("Final todos:", result.get("todos"))
print("Files created:", list(result.get("files", {}).keys()))
```

#### 3. Test Tools Individually

```python
# Test tools before passing to agent
result = my_tool("test input")
assert result is not None
```

#### 4. Validate Sub-agent Configs

```python
# Ensure all required fields
for subagent in subagents:
    assert "name" in subagent
    assert "description" in subagent
    assert "prompt" in subagent or "graph" in subagent
```

## Conclusion

The `deepagents` library provides a powerful framework for building sophisticated AI agents capable of handling complex, multi-step tasks. By combining planning tools, sub-agents, file systems, and detailed prompting, you can create agents that:

- Break down complex problems systematically
- Maintain context without pollution
- Produce high-quality, structured outputs
- Allow human oversight when needed

The key to success is understanding when to leverage each component:
- Use **sub-agents** for specialized work and context isolation
- Use **file tools** for persistent intermediate outputs
- Use **planning tools** for complex multi-step tasks
- Use **interrupts** for sensitive operations

With these patterns and practices, you can build deep agents tailored to your specific domain and requirements.