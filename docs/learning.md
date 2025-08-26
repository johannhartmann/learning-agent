# Learning System Architecture

## Overview

The Learning Agent employs a sophisticated learning system built on top of **LangMem** for memory management and **deepagents** for agent orchestration. The system enables the agent to learn from past experiences, apply learned patterns, and continuously improve its performance over time.

## Core Components

### 1. LangMem Integration (`learning/langmem_integration.py`)

The learning system uses LangMem's `ReflectionExecutor` for intelligent background processing of experiences:

```python
class LangMemLearningSystem:
    def __init__(self):
        self.memory_manager = create_memory_manager(...)
        self.reflection_executor = ReflectionExecutor(self.memory_manager)
```

**Key Features:**
- **Automatic Debouncing**: Multiple submissions are intelligently batched
- **Delayed Processing**: Configurable delays for optimal memory consolidation
- **Namespace Isolation**: Project-specific learning with `learning_agent` namespace
- **Persistent Storage**: Memories stored in `.agent/langmem/` directory

### 2. Learning Tools (`learning/tools.py`)

The agent has access to five specialized learning tools:

#### `search_memory`
- **Purpose**: Semantic search through past experiences
- **Usage**: Called at the start of tasks to find relevant prior knowledge
- **Returns**: Relevant memories from both LangMem storage and state
- **Example**: `search_memory("create a REST API")` returns past API implementations

#### `queue_learning`
- **Purpose**: Submit completed task executions for learning
- **Processing**: Immediate processing (0-second delay) for completed tasks
- **Data Captured**:
  - Task description and outcome (success/failure)
  - Execution context and duration
  - Error messages if failed
- **Integration**: Automatically triggers LangMem's ReflectionExecutor

#### `apply_pattern`
- **Purpose**: Apply high-confidence learned patterns
- **Threshold**: Only patterns with >80% confidence are applied
- **Tracking**: Updates pattern usage statistics

#### `create_memory`
- **Purpose**: Create explicit memories from experiences
- **Components**: Task, narrative, reflection, outcome
- **Storage**: Added to agent state for immediate access

#### `create_pattern`
- **Purpose**: Extract reusable patterns from experiences
- **Attributes**: Description, confidence level, success rate
- **Usage**: Patterns guide future task execution

### 3. State Management (`state.py`)

The `LearningAgentState` extends deepagents' base state with learning-specific fields:

```python
class LearningAgentState(DeepAgentState):
    memories: list[Memory] = []
    patterns: list[Pattern] = []
    learning_queue: list[ExecutionData] = []
    relevant_memories: list[str] = []
    applicable_patterns: list[str] = []
```

### 4. Agent Architecture (`agent.py`)

The main learning agent is created using deepagents framework:

```python
def create_learning_agent():
    # Initialize LangMem system
    initialize_learning_system(storage_path)

    # Create learning tools
    learning_tools = create_learning_tools()

    # Create deepagents agent with learning capabilities
    agent = create_deep_agent(
        tools=all_tools,
        instructions=LEARNING_AGENT_INSTRUCTIONS,
        model=llm,
        subagents=LEARNING_SUBAGENTS,
        state_schema=LearningAgentState,
    )
    return agent
```

## Learning Workflow

### 1. Task Reception
When a new task is received, the agent:
1. Searches for relevant past experiences using `search_memory`
2. Identifies applicable patterns from previous successes
3. Plans the task execution using `write_todos`

### 2. Task Execution
During execution, the agent:
1. Applies high-confidence patterns automatically
2. Tracks execution progress through todo states
3. Captures execution metrics (duration, errors, outcomes)

### 3. Post-Execution Learning
After task completion, the agent should:
1. Call `queue_learning` to submit the execution for processing
2. LangMem processes the experience immediately (0-second delay)
3. Memories are stored for future retrieval

### 4. Background Processing
LangMem's ReflectionExecutor handles:
- Memory consolidation and indexing
- Pattern extraction from repeated successes
- Semantic embedding for similarity search
- Automatic cleanup of redundant memories

## Sub-Agents

The system includes specialized sub-agents for complex learning tasks:

- **learning-query**: Searches and retrieves relevant learning data
- **execution-specialist**: Handles parallel task orchestration
- **reflection-analyst**: Performs deep analysis of completed tasks
- **planning-strategist**: Creates plans incorporating learned patterns

## Storage Structure

```
project/
└── .agent/
    └── langmem/
        ├── memories/      # Processed memories
        ├── patterns/      # Extracted patterns
        └── embeddings/    # Vector embeddings for search
```

## Configuration

### Environment Variables
- `LANGSMITH_API_KEY`: Required for tracing
- `LANGSMITH_PROJECT`: Project name (default: "learning-agent")
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`: LLM provider

### Model Configuration
Default model can be overridden in `config.py`:
```python
class Settings(BaseSettings):
    llm_model: str = "gpt-4o-mini"  # or "claude-3-opus", etc.
```

## UI Integration

The learning system integrates with the web UI to display:
- **Memories Panel**: Shows past experiences with narratives and reflections
- **Patterns View**: Displays learned patterns with confidence scores
- **Learning Queue**: Lists pending items for processing

## Troubleshooting

### Issue: Agent Not Calling queue_learning
**Symptom**: Tasks complete but no learning occurs
**Cause**: Model may not consistently follow complex instructions
**Solution**:
- Use more capable models (gpt-4, claude-3-opus)
- Add explicit reminders in prompts
- Consider adding automated post-execution hooks

### Issue: Empty LangMem Directory
**Symptom**: `.agent/langmem/` remains empty
**Cause**: Learning tools not being invoked
**Solution**: Verify agent is calling `queue_learning` after task completion

### Issue: No Streaming in UI
**Symptom**: Results appear all at once instead of streaming
**Cause**: Graph wrapper instead of direct deepagents graph
**Solution**: Use deepagents graph directly in `server.py`

### Issue: Memories Not Persisting
**Symptom**: Memories lost between sessions
**Cause**: Missing namespace configuration
**Solution**: Ensure `memory_manager.namespace = "learning_agent"` is set

## Best Practices

1. **Always Search First**: Begin tasks with `search_memory` to leverage past experiences
2. **Queue Everything**: Call `queue_learning` for both successes and failures
3. **High-Confidence Patterns**: Only apply patterns with >80% confidence automatically
4. **Immediate Processing**: Completed tasks use 0-second delay for instant learning
5. **Delayed Processing**: Ongoing conversations can use 30-second delays for batching

## Future Enhancements

- **Active Learning**: Proactively seek experiences to fill knowledge gaps
- **Cross-Project Learning**: Share patterns across multiple projects
- **Pattern Evolution**: Refine patterns based on new evidence
- **Forgetting Mechanism**: Remove outdated or incorrect patterns
- **Confidence Decay**: Reduce pattern confidence over time without reinforcement

## Technical Details

### LangMem ReflectionExecutor
- Handles asynchronous processing of experiences
- Automatically deduplicates similar memories
- Provides semantic search capabilities
- Manages memory lifecycle and cleanup

### Deepagents Integration
- Provides React agent architecture
- Enables tool calling and sub-agent orchestration
- Handles streaming and state management
- Integrates with LangGraph for graph-based execution

### Memory Processing Pipeline
1. **Submission**: Task data submitted via `queue_learning`
2. **Reflection**: LLM analyzes experience for insights
3. **Embedding**: Generate semantic embeddings for search
4. **Storage**: Persist to disk with metadata
5. **Indexing**: Update search indices for fast retrieval

## API Reference

See individual module documentation:
- `learning/langmem_integration.py` - LangMem system interface
- `learning/tools.py` - Learning tool implementations
- `state.py` - State schema definitions
- `agent.py` - Main agent configuration
