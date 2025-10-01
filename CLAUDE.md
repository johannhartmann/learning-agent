# Learning CLI Agent - Project Instructions

## Project Overview
A multi-agent learning system that captures and applies knowledge from past task executions. The system uses deep learning extraction to understand tactical, strategic, and meta-level insights from experiences, storing them in a vector database for similarity-based retrieval.

## Current Implementation Status
- ✅ **Core Agent**: LangGraph-based supervisor with subagent support
- ✅ **Learning System**: Multi-dimensional learning extraction (tactical, strategic, meta)
- ✅ **Vector Storage**: PostgreSQL + pgvector for semantic search
- ✅ **Execution Analysis**: Pattern detection and efficiency scoring
- ✅ **Subagent Support**: Parallel execution with streaming output
- ✅ **MCP Integration**: Browser tools for research subagent
- ✅ **Web UI**: CopilotKit-powered React interface at port 10300
- ✅ **Type Safety**: Full mypy compliance with strict typing

## Key Frameworks & Dependencies
- **langgraph**: Graph-based agent orchestration with checkpointing
- **langchain**: LLM abstractions and structured output
- **copilotkit**: Modern AI chat interface with streaming support
- **langmem**: Memory persistence (integrated with vector storage)
- **pgvector**: Vector similarity search in PostgreSQL
- **MCP (Model Context Protocol)**: Tool integration for browser automation
- **FastAPI**: REST API for memory access
- **uv**: Python package management
- **ruff**: Python linting (all checks passing)
- **mypy**: Static type checking

## Architecture Components

### 1. Supervisor Agent (`agent.py`)
- Built on LangGraph framework with create_react_agent
- Manages task execution flow and subagent orchestration
- Integrates with learning system for memory retrieval
- Supports parallel subagent execution with streaming
- State management with checkpointing support
- MCP browser tools integration for research tasks

### 2. Learning System
#### Vector Storage (`learning/vector_storage.py`)
- PostgreSQL with pgvector extension
- Separate task and content embeddings
- Stores deep learning dimensions:
  - Tactical learning (implementation insights)
  - Strategic learning (higher-level patterns)
  - Meta-learning (learning about learning)
  - Anti-patterns (what to avoid)
  - Execution metadata (tool usage, efficiency)

#### Learning Integration (`learning/langmem_integration.py`)
- LangChain structured output with Pydantic models
- Automatic learning extraction from conversations
- Task similarity search for relevant past experiences
- Pattern consolidation and confidence scoring

#### Execution Analyzer (`learning/execution_analyzer.py`)
- Analyzes tool usage sequences
- Identifies redundancies and inefficiencies
- Detects parallelization opportunities
- Calculates efficiency scores
- Provides execution patterns

### 3. API Server (`api_server.py`)
- FastAPI server on port 8001
- Endpoints for memory and pattern retrieval
- Pydantic models for structured responses
- CORS support for UI integration

### 4. Web UI (CopilotKit Integration)
- React + TypeScript frontend powered by CopilotKit
- Accessible at http://localhost:10300
- Features:
  - **CopilotChat**: Main conversational interface with streaming responses
  - **Task Panel**: Real-time task tracking and todo management
  - **Learning Panel**: Display of memories, patterns, and insights
  - **Artifacts Gallery**: Visual display of generated files and outputs
  - **LangGraph Integration**: Direct connection to LangGraph runtime via CopilotKit runtime
  - **Telemetry Disabled**: Privacy-focused with COPILOTKIT_TELEMETRY_DISABLED=true

## Project Structure
```
learning-agent/
├── pyproject.toml           # uv-based package management
├── src/
│   └── learning_agent/
│       ├── agent.py         # Main supervisor agent with subagent support
│       ├── api_server.py    # FastAPI server
│       ├── server.py        # LangGraph server
│       ├── state.py         # Agent state definitions
│       ├── config.py        # Settings management
│       ├── subagents.py     # Subagent definitions and management
│       ├── stream_adapter.py # Streaming output adapter
│       ├── learning/
│       │   ├── vector_storage.py      # PostgreSQL + pgvector
│       │   ├── langmem_integration.py # Learning extraction
│       │   ├── execution_analyzer.py  # Pattern detection
│       │   └── tools.py               # Learning tools
│       ├── tools/
│       │   ├── mcp_browser.py        # MCP browser integration
│       │   └── sandbox_tool.py       # Python sandbox execution
│       ├── mcp/
│       │   └── servers/
│       │       └── browser_use_stdioserver.py  # Browser MCP server
│       └── providers/       # LLM and embedding factories
├── tests/                   # 29 passing tests
├── docker-compose.yml       # Services orchestration
└── Dockerfile.server        # Container definitions
```

## Development Standards
- Python >=3.11
- Full type hints for all functions
- Docstrings for all public interfaces
- PEP 8 compliance
- Async/await for I/O operations
- Use ruff for linting
- Use mypy for type checking

## Execution Flow
1. **Task Reception**: Natural language input via CopilotChat interface
2. **Learning Query**: Search vector store for similar past executions
3. **Task Decomposition**: Break complex request into hierarchical todos
4. **Subagent Routing**: Dispatch to specialized subagents (research, coding, etc.)
5. **Parallel Orchestration**: LangGraph manages concurrent subagent execution
6. **Streaming Updates**: Real-time progress via CopilotKit streaming
7. **Result Aggregation**: Collect and merge results from all subagents
8. **Learning Extraction**: Store patterns in project learning database

## Key Implementation Requirements

### Parallel Execution
- Automatic dependency detection for parallelization
- No hard limit on parallel sub-agents (soft cap: 10 concurrent)
- Dynamic batching of independent todos
- Use langgraph Send API for fan-out/fan-in

### Learning Application
- Automatically apply high-confidence patterns (>90% success rate)
- No user confirmation for learned pattern application
- Adjust strategy in real-time based on execution feedback
- Store execution traces, patterns, and metadata in `.agent/` directory

### UI Requirements (CopilotKit)
- Natural language conversational interface via CopilotChat
- Rich web-based visualization with:
  - Streaming responses with markdown support
  - Real-time task tracking in dedicated panel
  - Learning insights and pattern display
  - Artifact gallery for generated files
  - Panel-based layout with switchable views (Tasks/Learning/Artifacts)
  - Direct integration with LangGraph runtime

### Tools
- **Planning Tool**: Create/update hierarchical todo structures with dependencies
- **Filesystem Tool**: Read/write files, manage directories with atomic operations
- **Python Sandbox**: Secure code execution with visualization support
- **MCP Browser Tools**: Web research and browser automation (research subagent)
- **Learning Tools**: Memory search and pattern retrieval

## Performance Constraints
- Sub-agent parallel execution cap: 10 concurrent
- Learning search timeout: 2 seconds
- Pattern application decision: <100ms
- Max learning database size: 1GB per project

## Important References
- CopilotKit Docs: https://docs.copilotkit.ai/
- LangGraph Send API: https://langchain-ai.github.io/langgraph/how-tos/send/
- LangGraph Supervisor Pattern: https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/
- LangMem Memory Store: https://github.com/langchain-ai/langmem#memory-store
- MCP Protocol: https://modelcontextprotocol.io/

## CopilotKit Configuration
- **Runtime URL**: `/api/copilotkit` - Connects to LangGraph backend
- **Agent Key**: `learning_agent` - Primary agent identifier
- **Deployment URL**: Configured via `NEXT_PUBLIC_DEPLOYMENT_URL` or defaults to `http://server:2024`
- **Telemetry**: Disabled by default (`COPILOTKIT_TELEMETRY_DISABLED=true`)
- **Components**:
  - `CopilotChat`: Main chat interface with streaming support
  - `useCopilotContext`: Access to agent state and context
  - `useCopilotReadable`: Real-time state synchronization

## Docker Services
```yaml
services:
  postgres:     # Port 5433 - PostgreSQL with pgvector
  server:       # Port 8000 - LangGraph server
  api-server:   # Port 8001 - FastAPI memory API
  ui:           # Port 10300 - CopilotKit React interface
```

## Testing & Quality Assurance
- **Unit Tests**: 29 tests all passing
- **Type Checking**: Zero mypy errors
- **Linting**: All ruff checks passing
- **Pre-commit hooks**: Enforced on all commits
  - ruff (linting & formatting)
  - mypy (type checking)
  - bandit (security scanning)
  - commitizen (commit format)

## Development Guidelines
- You are working in a conda environment, so do not use venv
- Always use LangChain structured output (https://python.langchain.com/docs/how_to/structured_output/)
- Never parse LLM results manually
- Never create redundant implementations - refactor existing code
- Never maintain outdated code for backward compatibility
- Never bypass errors - fix them properly
- Never skip mypy for commits - all type errors must be resolved
- Use isinstance() checks for structured output validation
- Prefer Playwright MCP for e2e testing over curl
- Validate UI changes using Playwright browser automation

## Key Learnings & Patterns
1. **Structured Output**: Always use `llm.with_structured_output(PydanticModel)` and check with `isinstance()`
2. **Type Safety**: Add type annotations for all functions, use `type: ignore` sparingly
3. **Vector Search**: Separate embeddings for task similarity vs content similarity
4. **Execution Analysis**: Track tool sequences to identify inefficiencies
5. **Memory Structure**: Store multi-dimensional insights (tactical, strategic, meta)
6. **API Design**: Use Pydantic models for all API request/response schemas
- Use playwright MCP to test the frontend
- Use docker to test the integration
- if you want to test the code after a change you need to rebuild the docker container
- Do not start, stop or rebuild docker on your own, you are proven to stupid to do it.
- ask the user to rebuild and restart instead.
