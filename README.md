# 🧠 Learning Agent

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)](http://mypy-lang.org/)
[![LangSmith](https://img.shields.io/badge/LangSmith-Enabled-green)](https://smith.langchain.com)
[![CI](https://github.com/johannhartmann/learning-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/johannhartmann/learning-agent/actions/workflows/ci.yml)

A sophisticated autonomous agent system that learns from experience, orchestrates parallel task execution, and adapts its behavior based on past successes and failures.

## ✨ Features

- **🎭 DeepAgents Framework**: Built on [deepagents](https://github.com/langchain-ai/deepagents) for sophisticated agent orchestration
- **🐘 PostgreSQL Vector Storage**: Production-ready vector database with pgvector for semantic memory search
- **🔄 Multi-Dimensional Learning**: Captures tactical, strategic, and meta-level insights from every execution
- **⚡ Parallel Sub-Agents**: Four specialized sub-agents (learning-query, execution-specialist, reflection-analyst, planning-strategist)
- **🌐 REST API Server**: FastAPI endpoints for memory retrieval and pattern analysis (port 8001)
- **📝 Narrative Memory**: Creates human-readable narratives of experiences with deep reflection
- **🔍 Execution Analysis**: Automatic detection of inefficiencies, redundancies, and optimization opportunities
- **🗂️ Virtual File System**: Safe file operations through deepagents' virtual filesystem
- **📊 LangSmith Integration**: Complete observability of agent execution and learning processes
- **🖥️ Web UI**: React-based interface for visual interaction with the agent (port 10300)

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- OpenAI API key or other supported LLM provider
- Docker and Docker Compose (for UI)

### Installation

```bash
# Clone the repository
git clone https://github.com/johannhartmann/learning-agent.git
cd learning-agent

# Install with uv (recommended)
uv sync --all-extras

# Or install with pip
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Basic Usage

```python
import asyncio
from learning_agent.learning_supervisor import LearningSupervisor

async def main():
    # Initialize the learning supervisor
    supervisor = LearningSupervisor()

    # Process a task - the agent will plan, execute, and learn
    result = await supervisor.process_task(
        "Create a Python function to calculate fibonacci numbers and test it"
    )

    print(f"Task completed: {result['status']}")
    print(f"Summary: {result['summary']}")

    # The agent has now learned from this experience
    # Future similar tasks will be executed more efficiently

    await supervisor.shutdown()

asyncio.run(main())
```

### 🖥️ Web UI

The Learning Agent includes a React-based web UI for visual interaction with the agent system.

#### Quick Start with Docker (Recommended)

```bash
# Build and start all services (PostgreSQL, API server, LangGraph server, UI)
make docker-up

# Access the services:
# - Web UI: http://localhost:10300
# - LangGraph Server: http://localhost:2024
# - API Server: http://localhost:8001
# - PostgreSQL: localhost:5433
```

#### Manual Setup

1. **Start PostgreSQL with pgvector**:
```bash
docker run -d \
  --name learning-agent-db \
  -e POSTGRES_USER=learning_agent \
  -e POSTGRES_PASSWORD=learning_agent_pass \
  -e POSTGRES_DB=learning_memories \
  -p 5433:5432 \
  pgvector/pgvector:pg16
```

2. **Start the LangGraph Server**:
```bash
make server-dev  # Runs on port 2024
```

3. **Start the API Server** (in a new terminal):
```bash
make api-server  # Runs on port 8001
```

4. **Start the UI** (in another terminal):
```bash
make ui-dev  # Runs on port 10300
```

#### Docker Commands

```bash
# Build Docker images
make docker-build

# Start containers
make docker-up

# View logs
make docker-logs

# Stop containers
make docker-down

# Clean up (including volumes)
make docker-clean
```

### Using the DeepAgents API Directly

```python
from learning_agent.agent import create_learning_agent
from learning_agent.state import LearningAgentState

# Create a deepagents-based learning agent
agent = create_learning_agent()

# Create initial state
initial_state: LearningAgentState = {
    "messages": [{"role": "user", "content": "Your task here"}],
    "todos": [],
    "files": {},
    "memories": [],
    "patterns": [],
    "learning_queue": [],
}

# Execute task
result = await agent.ainvoke(initial_state)
```

## 🏗️ Architecture

The Learning Agent combines DeepAgents framework with PostgreSQL vector storage, API server, and web UI:

```mermaid
graph TD
    UI[React Web UI] -->|HTTP| API[FastAPI Server :8001]
    UI -->|WebSocket| Server[LangGraph Server :2024]

    CLI[CLI Interface] --> LS[LearningSupervisor]
    Server --> LS

    LS -->|Orchestrates| Agent[DeepAgents Agent]
    Agent --> Tools[Core Tools]
    Agent --> SubAgents[Sub-Agents via Task Tool]

    Tools --> PT[Planning Tool - write_todos]
    Tools --> FS[File System - read/write/edit]
    Tools --> LT[Learning Tools]

    SubAgents --> LQ[learning-query]
    SubAgents --> ES[execution-specialist]
    SubAgents --> RA[reflection-analyst]
    SubAgents --> PS[planning-strategist]

    LS -->|Background Processing| NL[NarrativeLearner]
    NL -->|Stores| PG[(PostgreSQL + pgvector :5433)]

    API -->|Queries| PG
    LT -->|Search| PG

    PG -->|Stores| Memories[Multi-Dimensional Memories]
    PG -->|Stores| Patterns[Execution Patterns]
    PG -->|Stores| Embeddings[Vector Embeddings]
```

### Core Components

- **React Web UI** (Port 10300): TypeScript-based interface for visual interaction
- **FastAPI Server** (Port 8001): REST API for memory retrieval and pattern analysis
- **LangGraph Server** (Port 2024): Serves the agent as an API endpoint
- **PostgreSQL + pgvector** (Port 5433): Production-ready vector database for semantic search
- **LearningSupervisor**: Orchestrates deepagents agent with background learning
- **DeepAgents Agent**: Core agent built with `create_deep_agent()`
- **NarrativeLearner**: Processes conversations into multi-dimensional learnings
- **Specialized Sub-Agents**: Four agents for different execution aspects
- **Learning Tools**: Memory search, pattern application, and learning queue management

## 🌐 API Server

The FastAPI server provides REST endpoints for accessing memories and patterns:

### Endpoints

- `GET /memories` - Retrieve stored memories with optional search
- `GET /patterns` - Get identified patterns with confidence scores
- `GET /learning-queue` - View items queued for learning
- `GET /execution-stats` - Get execution efficiency metrics

### Example Usage

```bash
# Get recent memories
curl http://localhost:8001/memories?limit=10

# Search memories by content
curl http://localhost:8001/memories?search=fibonacci

# Get high-confidence patterns
curl http://localhost:8001/patterns?min_confidence=0.8
```

## 🧪 Testing

The project includes comprehensive test coverage with CI/CD integration:

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests
make test-integration   # Integration tests

# Run with coverage
make test-coverage

# Type checking
make typecheck

# Linting
make lint
```

### CI/CD Pipeline
- **GitHub Actions**: Automated testing on every push
- **Test Matrix**: Python 3.11 and 3.12
- **Quality Checks**: Linting, type checking, security scanning
- **Coverage**: Unit tests with pytest-cov
- **API Key Safety**: Tests skip when API keys unavailable

## 📊 Observability

The agent provides full observability through LangSmith:

1. **Trace Every Decision**: Complete visibility into planning and execution
2. **Learning Metrics**: Track pattern recognition and application
3. **Performance Monitoring**: Latency, token usage, and cost tracking
4. **Anomaly Detection**: Automatic detection of behavioral changes

Configure LangSmith in your `.env`:
```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_api_key
LANGSMITH_PROJECT=learning-agent
```

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
make install-dev

# Install pre-commit hooks
make pre-commit-install

# Run all quality checks
make check
```

### Available Commands

```bash
make help              # Show all available commands
make test             # Run tests
make lint             # Run linting
make format           # Format code
make typecheck        # Type checking
make security         # Security scan
make deadcode         # Find unused code
```

### Code Quality

- **Linting**: Ruff with extensive rule set
- **Type Checking**: Strict mypy configuration
- **Security**: Bandit for security issues
- **Dead Code**: Vulture for unused code detection
- **Coverage**: Pytest-cov with 52% traditional coverage + LangSmith probabilistic testing

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`make test-all`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📚 Documentation

- [Testing Strategy](tests/README.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 🐘 PostgreSQL Vector Storage

The Learning Agent uses PostgreSQL with pgvector extension for production-ready vector storage:

### Features
- **Multi-Dimensional Learning Storage**: Stores tactical, strategic, and meta-level insights
- **Semantic Search**: Vector similarity search for finding relevant past experiences
- **Execution Pattern Analysis**: Tracks tool usage, efficiency scores, and anti-patterns
- **Scalable**: Production-ready database that can handle millions of memories

### Database Schema
- **Memories Table**: Stores conversation memories with embeddings
- **Patterns Table**: Stores identified patterns and their confidence scores
- **Learning Queue**: Tracks items queued for explicit learning
- **Execution Metadata**: Stores tool sequences, timings, and efficiency metrics

### Connection
```env
DATABASE_URL=postgresql://learning_agent:learning_agent_pass@localhost:5433/learning_memories
```

## 🔧 Configuration

The agent is highly configurable through environment variables:

```env
# LLM Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7

# API Keys
OPENAI_API_KEY=your_api_key
ANTHROPIC_API_KEY=your_api_key  # Optional
LANGSMITH_API_KEY=your_api_key

# Database Configuration
DATABASE_URL=postgresql://learning_agent:learning_agent_pass@localhost:5433/learning_memories

# Learning Configuration
ENABLE_LEARNING=true
LEARNING_CONFIDENCE_THRESHOLD=0.9
PATTERN_RETENTION_DAYS=90

# Performance
MAX_PARALLEL_AGENTS=10
TASK_TIMEOUT_SECONDS=300

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

See [.env.example](.env.example) for all options.

## 🚦 Project Status

This project is in active development.

### ✅ Completed Features
- [x] PostgreSQL vector storage with pgvector
- [x] Multi-dimensional learning extraction (tactical, strategic, meta)
- [x] Web UI with React/TypeScript
- [x] REST API for memory access
- [x] Execution pattern analysis
- [x] Support for multiple LLM providers (OpenAI, Anthropic, Ollama, etc.)
- [x] CI/CD pipeline with GitHub Actions

### 🚧 In Progress
- [ ] Long-term memory consolidation
- [ ] Advanced pattern recognition algorithms
- [ ] Collaborative multi-agent learning
- [ ] Memory pruning and optimization
- [ ] Real-time learning dashboard

## 📝 License

License to be determined.

## 🙏 Acknowledgments

Built with:
- [LangChain](https://langchain.com/) - LLM orchestration
- [LangGraph](https://langchain-ai.github.io/langgraph/) - State machine orchestration
- [LangSmith](https://smith.langchain.com/) - Observability and testing
- [Rich](https://rich.readthedocs.io/) - Terminal UI

## 📬 Contact

Johann Hartmann - [@johannhartmann](https://github.com/johannhartmann)

Project Link: [https://github.com/johannhartmann/learning-agent](https://github.com/johannhartmann/learning-agent)
