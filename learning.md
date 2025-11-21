# Learning Agent - Learning System Architecture

This document focuses exclusively on the **learning system** components: how the agent captures, processes, stores, and retrieves knowledge from past executions.

---

## 1. Learning System Flow

```mermaid
graph TB
    conversation[Conversation Messages]

    subgraph reflection[Background Reflection]
        direction TB
        executor[ReflectionExecutor<br/>delay=0s]
        process[_process_and_store_memory]

        executor --> process
    end

    conversation --> executor

    subgraph processing[Learning Processing]
        direction TB
        p1[Convert to narrative]
        p2[ExecutionAnalyzer<br/>analyze_conversation]
        p3[Compute relevance signals]
        p4{Has meaningful<br/>signals?}
        p5[LLM: Extract learnings<br/>with structured output]
        p6{should_save<br/>== True?}

        p1 --> p2
        p2 --> p3
        p3 --> p4
        p4 -->|Yes| p5
        p4 -->|No| skip[Skip]
        p5 --> p6
        p6 -->|Yes| store
        p6 -->|No| skip2[Skip]
    end

    process --> p1

    subgraph storage[Vector Storage]
        direction TB
        store[Store in PostgreSQL]
        emb1[Generate task_embedding<br/>from task field]
        emb2[Generate content_embedding<br/>from all learning dimensions]
        db[(PostgreSQL + pgvector<br/>memories table)]

        store --> emb1
        store --> emb2
        emb1 --> db
        emb2 --> db
    end

    subgraph update[State Update]
        direction TB
        patch[HTTP PATCH to<br/>LangGraph server]
        ui[Update UI with<br/>new memory]

        patch --> ui
    end

    db --> update

    style reflection fill:#e1f5ff
    style processing fill:#fff4e1
    style storage fill:#e8f5e9
    style update fill:#fce4ec
```

---

## 2. Vector Storage Schema

```mermaid
erDiagram
    MEMORIES {
        uuid id PK
        text task
        text context
        text narrative
        text reflection
        text tactical_learning
        text strategic_learning
        text meta_learning
        jsonb anti_patterns
        jsonb execution_metadata
        float confidence_score
        text outcome
        timestamptz timestamp
        jsonb metadata
        vector_1536 embedding "Content similarity"
        vector_1536 task_embedding "Task similarity"
    }

    MEMORIES ||--o{ EMBEDDING_INDEX : "ivfflat index"
    MEMORIES ||--o{ TASK_EMBEDDING_INDEX : "ivfflat index"
```

### Learning Dimensions Stored

| Dimension | Type | Purpose | Example |
|-----------|------|---------|---------|
| **tactical_learning** | TEXT | Specific implementation insights | "Use Pydantic BaseModel for FastAPI request validation" |
| **strategic_learning** | TEXT | Higher-level patterns and approaches | "API-first design allows parallel frontend/backend development" |
| **meta_learning** | TEXT | Learning about the learning process itself | "Always test endpoints before deploying to avoid rollback" |
| **anti_patterns** | JSONB | What NOT to do, inefficiencies found | `{"description": "Don't read file multiple times", "redundancies": [...]}` |
| **execution_metadata** | JSONB | Tool usage patterns, efficiency metrics | `{"tool_counts": {...}, "efficiency_score": 0.78}` |

---

## 3. Dual Embedding Strategy

```mermaid
graph LR
    subgraph input[Memory Input]
        direction TB
        task[Task: Build FastAPI endpoint]
        tactical[Tactical: Use Pydantic models]
        strategic[Strategic: API-first design]
        meta[Meta: Test before deploy]
    end

    subgraph embeddings[Embedding Generation]
        direction TB
        task_emb[Task Embedding<br/>From: task only]
        content_emb[Content Embedding<br/>From: task + tactical +<br/>strategic + meta]
    end

    subgraph queries[Query Types]
        direction TB
        q1[Similar Task Query:<br/>What tasks like this<br/>have I done?]
        q2[Content Query:<br/>What do I know<br/>about X?]
    end

    input --> embeddings

    task --> task_emb
    task --> content_emb
    tactical --> content_emb
    strategic --> content_emb
    meta --> content_emb

    task_emb -.->|Uses| q1
    content_emb -.->|Uses| q2

    style input fill:#e1f5ff
    style embeddings fill:#fff4e1
    style queries fill:#e8f5e9
```

### Why Dual Embeddings?

**Problem**: Task names don't always reflect the knowledge contained in the learning.

**Example**:
- **Task**: "Build FastAPI endpoint"
- **Content**: Detailed API security best practices, authentication patterns, error handling

**Solution**: Two separate embeddings for two different query types:

1. **Task Embedding** (`task_embedding`)
   - Generated from: `task` field only
   - Query: `ORDER BY task_embedding <=> $query`
   - Use case: "Show me tasks similar to building a REST API"
   - SQL: `SELECT * FROM memories WHERE task_embedding <=> embed("Build REST API") LIMIT 5`

2. **Content Embedding** (`embedding`)
   - Generated from: `task + reflection + tactical_learning + strategic_learning + meta_learning`
   - Query: `ORDER BY embedding <=> $query`
   - Use case: "What do I know about API authentication?"
   - SQL: `SELECT * FROM memories WHERE embedding <=> embed("API authentication") LIMIT 5`

### Search Comparison

| Query | Task Embedding Match | Content Embedding Match |
|-------|---------------------|------------------------|
| "Build FastAPI endpoint" | ✅ High similarity | ⚠️ Medium similarity |
| "API security patterns" | ❌ Low similarity | ✅ High similarity |
| "Deploy Python service" | ⚠️ Medium similarity | ⚠️ Medium similarity |

---

## 4. Execution Analyzer

```mermaid
graph TB
    messages[Conversation Messages]

    subgraph extraction[Tool Extraction]
        direction TB
        e1[Extract tool calls<br/>from message content]
        e2[Build tool_sequence array]
        e3[Count tool usage]
    end

    messages --> extraction

    subgraph analysis[Pattern Analysis]
        direction TB
        a1[Identify Redundancies]
        a2[Identify Inefficiencies]
        a3[Find Parallelization<br/>Opportunities]
        a4[Extract Execution Patterns]
        a5[Calculate Efficiency Score]
    end

    extraction --> analysis

    subgraph redundancies[Redundancy Types]
        direction TB
        r1[Consecutive duplicates]
        r2[Excessive todo updates]
        r3[Unnecessary ls calls]
    end

    a1 --> redundancies

    subgraph inefficiencies[Inefficiency Types]
        direction TB
        i1[No initial plan]
        i2[Read without context]
        i3[Repeated reads]
    end

    a2 --> inefficiencies

    subgraph output[Analysis Output]
        direction TB
        o1[tool_sequence: Array]
        o2[tool_counts: Object]
        o3[redundancies: Array]
        o4[inefficiencies: Array]
        o5[parallelization_opportunities: Array]
        o6[execution_patterns: Object]
        o7[efficiency_score: 0.0-1.0]
    end

    analysis --> output

    style extraction fill:#e1f5ff
    style analysis fill:#fff4e1
    style redundancies fill:#ffebee
    style inefficiencies fill:#fff3e0
    style output fill:#e8f5e9
```

### Execution Analysis Output

**Example Output**:
```json
{
  "tool_sequence": ["write_todos", "read_file", "read_file", "write_file"],
  "tool_counts": {
    "write_todos": 1,
    "read_file": 2,
    "write_file": 1
  },
  "total_tool_calls": 4,
  "unique_tools_used": 3,
  "redundancies": [
    {
      "type": "consecutive_duplicate",
      "tool": "read_file",
      "position": 2,
      "suggestion": "Batch read_file operations"
    }
  ],
  "inefficiencies": [],
  "parallelization_opportunities": [],
  "execution_patterns": {
    "starts_with_plan": true,
    "uses_todos": true,
    "delegates_to_subagent": false,
    "uses_python_sandbox": false,
    "dominant_tool": "read_file",
    "tool_diversity": 0.75,
    "workflow_pattern": "plan_execute"
  },
  "efficiency_score": 0.85
}
```

### Efficiency Score Calculation

```python
score = 1.0
score -= min(redundancy_count * 0.1, 0.3)       # Max -0.3
score -= min(inefficiency_count * 0.15, 0.3)    # Max -0.3
score -= min(parallel_missed * 0.1, 0.2)        # Max -0.2
score += 0.1 if starts_with_todos else 0.0      # Bonus
score += 0.05 if uses_sandbox else 0.0          # Bonus
```

**Range**: 0.0 (highly inefficient) → 1.0 (optimal)

---

## 5. Relevance Signal Detection

```mermaid
graph TB
    conversation[Conversation + Metadata]

    subgraph signals[Relevance Signals]
        direction TB
        s1{Tool usage > 0?}
        s2{Analysis findings?}
        s3{Tool messages?}
        s4{Completed tasks > 0?}
        s5{Todo progress?}
        s6{Failure outcome?}
        s7{Execution error?}
    end

    conversation --> signals

    s1 -->|Yes| add1[Add: tool_usage]
    s2 -->|Yes| add2[Add: analysis_findings]
    s3 -->|Yes| add3[Add: tool_messages]
    s4 -->|Yes| add4[Add: completed_tasks]
    s5 -->|Yes| add5[Add: todo_progress]
    s6 -->|Yes| add6[Add: failure_outcome]
    s7 -->|Yes| add7[Add: execution_error]

    subgraph decision[Learning Decision]
        direction TB
        d1{Any signals?}
        d2[Submit for learning]
        d3[Skip learning]

        d1 -->|Yes| d2
        d1 -->|No| d3
    end

    add1 --> decision
    add2 --> decision
    add3 --> decision
    add4 --> decision
    add5 --> decision
    add6 --> decision
    add7 --> decision

    style signals fill:#fff4e1
    style decision fill:#e8f5e9
```

### Relevance Signals Reference

| Signal | Condition | Why It Matters |
|--------|-----------|----------------|
| **tool_usage** | `total_tool_calls > 0` | Agent interacted with environment |
| **tool_messages** | ToolMessage in conversation | Concrete tool execution happened |
| **analysis_findings** | Analyzer found redundancies/inefficiencies | Patterns worth learning from |
| **completed_tasks** | `completed_count > 0` in metadata | Tasks were actually finished |
| **todo_progress** | Todo status changed from pending | Work was tracked and executed |
| **failure_outcome** | `outcome == "failure"` | Failures are valuable learning |
| **execution_error** | Error occurred during execution | Anti-patterns to avoid |

### Decision Logic

```python
relevance_signals = compute_learning_relevance_signals(
    messages=messages,
    metadata=metadata,
    execution_analysis=execution_analysis,
)

if not relevance_signals:
    logger.info("Skipping learning: no relevance signals detected")
    return  # Don't store trivial conversations

# Proceed to LLM-based learning extraction...
```

**Design Philosophy**:
- Don't store every conversation (avoids noise)
- Only store when there's evidence of actual work
- LLM makes final `should_save` decision based on value

---

## 6. Learning Extraction Process

```mermaid
sequenceDiagram
    participant Graph as Main Graph
    participant Executor as ReflectionExecutor
    participant Processor as _process_and_store_memory
    participant Analyzer as ExecutionAnalyzer
    participant LLM as Structured LLM
    participant Storage as VectorLearningStorage
    participant Server as LangGraph Server

    Graph->>Executor: submit_conversation_for_learning<br/>(delay=0s)
    Executor->>Processor: Process in background

    Processor->>Processor: Convert to narrative
    Processor->>Analyzer: analyze_conversation()
    Analyzer-->>Processor: execution_analysis

    Processor->>Processor: compute_relevance_signals()

    alt No relevance signals
        Processor->>Processor: Skip learning
    else Has relevance signals
        Processor->>LLM: Extract learnings<br/>(structured output)
        LLM-->>Processor: LearningExtraction<br/>{learnings, confidence, should_save}

        alt should_save == False
            Processor->>Processor: Skip learning
        else should_save == True
            Processor->>Storage: store_memory()
            Storage->>Storage: Generate task_embedding
            Storage->>Storage: Generate content_embedding
            Storage->>Storage: INSERT into memories table
            Storage-->>Processor: memory_id

            Processor->>Server: HTTP PATCH /threads/{id}/state
            Server-->>Processor: State updated
        end
    end
```

### Structured Learning Extraction

**Input Prompt** (sent to LLM):
```
Analyze this task execution and extract actionable learnings for similar future tasks.

Focus on:
- What approach worked well or didn't work
- Key insights about tools, patterns, techniques
- Important pitfalls to avoid
- Efficient workflows or shortcuts discovered

CONVERSATION:
[full narrative with all messages]

EXECUTION ANALYSIS:
- Tool usage pattern: plan_execute
- Efficiency score: 0.78
- Redundancies found: 2
- Inefficiencies found: 1
- Parallelization opportunities: 0

Redundancy details: [specific redundancies]
Inefficiency details: [specific inefficiencies]

Extract learnings only when they provide tangible value for future similar tasks.
```

**Output Schema** (Pydantic):
```python
class LearningExtraction(BaseModel):
    learnings: str  # Key actionable learnings
    confidence_score: float = 0.5  # 0.0-1.0
    should_save: bool = True  # LLM decides
    save_reason: str | None = None  # Justification
```

**Example Output**:
```json
{
  "learnings": "When building REST APIs with FastAPI, use Pydantic BaseModel for request/response validation. This provides automatic data validation, serialization, and OpenAPI schema generation. For authentication, prefer dependency injection with Depends() to keep endpoints clean.",
  "confidence_score": 0.85,
  "should_save": true,
  "save_reason": "Contains reusable patterns for FastAPI development with specific tool recommendations"
}
```

---

## 7. Learning Retrieval Flow

```mermaid
graph TB
    user_msg[User Message]

    subgraph fetch_node[fetch_relevant_learnings Node]
        direction TB
        f1[Extract latest human message]
        f2{First message<br/>in thread?}
        f3a[Use raw message content]
        f3b[Synthesize task context<br/>from last 10 messages]
        f4[Generate query embedding]
        f5[Search vector DB:<br/>search_similar_tasks<br/>limit=3]
        f6[Format learnings as<br/>SystemMessage]
        f7[Inject into conversation]
    end

    user_msg --> fetch_node

    f1 --> f2
    f2 -->|Yes| f3a
    f2 -->|No| f3b
    f3a --> f4
    f3b --> f4
    f4 --> f5

    subgraph vector_search[Vector Similarity Search]
        direction TB
        v1[(memories table)]
        v2[ORDER BY<br/>task_embedding <=> query]
        v3[LIMIT 3]

        v1 --> v2
        v2 --> v3
    end

    f5 --> vector_search
    vector_search --> f6
    f6 --> f7

    subgraph injected_format[Injected SystemMessage Format]
        direction TB
        i1["Relevant prior learnings from similar tasks:"]
        i2["Task: [task] (outcome: success, confidence: 0.85)"]
        i3["Tactical: [tactical insights]"]
        i4["Strategic: [strategic patterns]"]
        i5["Meta: [meta learnings]"]
        i6["Anti-patterns: [what to avoid]"]

        i1 --> i2
        i2 --> i3
        i3 --> i4
        i4 --> i5
        i5 --> i6
    end

    f7 --> injected_format
    injected_format --> agent[Agent Execution<br/>with enriched context]

    style fetch_node fill:#e1f5ff
    style vector_search fill:#fff4e1
    style injected_format fill:#e8f5e9
```

### Retrieval Example

**User Message**: "Build a Python REST API with authentication"

**Search Query** (task embedding): `embed("Build a Python REST API with authentication")`

**SQL Query**:
```sql
SELECT
    id, task, reflection,
    tactical_learning, strategic_learning, meta_learning,
    anti_patterns, execution_metadata, confidence_score,
    outcome, context, timestamp, metadata,
    1 - (task_embedding <=> $query_embedding) as similarity
FROM memories
WHERE task_embedding IS NOT NULL
ORDER BY task_embedding <=> $query_embedding
LIMIT 3
```

**Retrieved Memories**:
1. **Task**: "Create FastAPI service with JWT auth" (similarity: 0.92)
   - Tactical: Use Pydantic models for validation, `python-jose` for JWT
   - Strategic: Separate auth logic into dependencies
   - Anti-patterns: Don't store secrets in code

2. **Task**: "Build REST API with database" (similarity: 0.87)
   - Tactical: Use SQLAlchemy async, connection pooling
   - Strategic: API-first design allows parallel development

3. **Task**: "Implement OAuth2 authentication" (similarity: 0.81)
   - Tactical: Use `fastapi.security.OAuth2PasswordBearer`
   - Meta: Test token expiration logic thoroughly

**Injected SystemMessage**:
```
Relevant prior learnings from similar tasks:

Task: Create FastAPI service with JWT auth (outcome: success, confidence: 0.92)
Tactical: Use Pydantic models for request validation. Use python-jose for JWT token generation.
Strategic: Separate authentication logic into FastAPI dependencies for clean endpoint code.
Anti-patterns: Don't store JWT secrets in code; use environment variables

Task: Build REST API with database (outcome: success, confidence: 0.87)
Tactical: Use SQLAlchemy async mode with connection pooling for better performance.
Strategic: API-first design allows frontend and backend teams to work in parallel.

Task: Implement OAuth2 authentication (outcome: success, confidence: 0.81)
Tactical: Use fastapi.security.OAuth2PasswordBearer for token dependency injection.
Meta: Always test token expiration and refresh logic before deploying to production.
```

---

## 8. Learning Data Flow

```mermaid
graph TB
    subgraph execution[Task Execution Phase]
        direction LR
        user[User Input] --> graph[Main Graph]
        graph --> agent[Agent Executes]
        agent --> tools[Tool Calls]
    end

    subgraph capture[Capture Phase]
        direction TB
        messages[Conversation Messages]
        metadata[Execution Metadata]
        state[Agent State]

        messages --- metadata
        metadata --- state
    end

    tools --> capture

    subgraph processing[Processing Phase]
        direction TB
        narrative[Convert to Narrative]
        analyze[ExecutionAnalyzer]
        signals[Relevance Signals]
        llm_extract[LLM Extraction]

        narrative --> analyze
        analyze --> signals
        signals --> llm_extract
    end

    capture --> processing

    subgraph storage[Storage Phase]
        direction TB
        task_emb[Task Embedding<br/>text-embedding-3-small]
        content_emb[Content Embedding<br/>text-embedding-3-small]
        postgres[(PostgreSQL + pgvector)]

        task_emb --> postgres
        content_emb --> postgres
    end

    llm_extract -->|if should_save| storage

    subgraph retrieval[Retrieval Phase - Next Task]
        direction TB
        new_task[New User Input]
        query_emb[Generate Query Embedding]
        search[Vector Similarity Search]
        inject[Inject Learnings]

        new_task --> query_emb
        query_emb --> search
        search --> inject
    end

    storage -.->|Vector Search| retrieval
    postgres -.->|Task Similarity| search
    retrieval --> execution

    style execution fill:#e1f5ff
    style capture fill:#fff4e1
    style processing fill:#ffe4b5
    style storage fill:#e8f5e9
    style retrieval fill:#fce4ec
```

---

## Key Implementation Details

### Code References

| Component | File | Lines | Key Function |
|-----------|------|-------|--------------|
| **Learning Submission** | `server.py` | 112-153 | `submit_learning_node()` |
| **Learning Retrieval** | `server.py` | 155-276 | `fetch_relevant_learnings_node()` |
| **Vector Storage** | `learning/vector_storage.py` | 15-321 | `VectorLearningStorage` |
| **Execution Analysis** | `learning/execution_analyzer.py` | 8-262 | `ExecutionAnalyzer` |
| **Learning Integration** | `learning/langmem_integration.py` | 123-554 | `LangMemLearningSystem` |
| **Relevance Signals** | `learning/langmem_integration.py` | 39-89 | `compute_learning_relevance_signals()` |

### Configuration

**Environment Variables**:
```bash
DATABASE_URL=postgresql://learning_agent:pass@postgres:5432/learning_memories
OPENAI_API_KEY=sk-...
LEARNING_BACKGROUND_DELAY=30  # Unused (set to 0 in code)
```

**Embedding Model**:
```python
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
# Output dimension: 1536
```

**Vector Index**:
```sql
CREATE INDEX memories_task_embedding_idx
ON memories USING ivfflat (task_embedding vector_cosine_ops)
WITH (lists = 100);
```

### Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| **Vector Search** | <50ms | Top-5 search with IVFFlat index |
| **Learning Extraction** | 1-3s | LLM call for structured output |
| **Embedding Generation** | 100-200ms | OpenAI API call per embedding |
| **Storage Write** | 50-100ms | PostgreSQL INSERT with embeddings |
| **State Update** | 50-100ms | HTTP PATCH to LangGraph server |

---

## Design Philosophy

### 1. **Automatic Learning**
- No explicit "learn" tool for the agent
- Learning happens automatically after each conversation
- Agent focuses on execution, not meta-learning

### 2. **Quality over Quantity**
- Relevance signals filter out trivial conversations
- LLM decides `should_save` based on value
- High confidence threshold (>0.5) for important learnings

### 3. **Multi-Dimensional Knowledge**
- Tactical: Implementation details
- Strategic: High-level patterns
- Meta: Process improvements
- Anti-patterns: What to avoid

### 4. **Separate Concerns**
- Task similarity ≠ Content similarity
- Dual embeddings enable precise retrieval
- Choose search strategy based on query type

### 5. **Non-Blocking**
- Learning happens in background
- Agent doesn't wait for learning to complete
- State updates are best-effort (failures don't break execution)

### 6. **Execution-Aware**
- Execution Analyzer detects patterns from tool usage
- Efficiency scores quantify performance
- Anti-patterns captured from redundancies/inefficiencies

---

## Future Enhancements

### Potential Improvements

1. **Multi-Dimensional Embeddings**
   - Separate embeddings for tactical/strategic/meta
   - More precise retrieval per learning dimension

2. **Confidence Decay**
   - Reduce confidence over time for old learnings
   - Weight recent learnings higher

3. **Learning Feedback Loop**
   - Track whether applied learnings succeeded
   - Update confidence based on outcomes
   - Remove consistently unhelpful learnings

4. **Pattern Library**
   - Consolidate repeated patterns into reusable templates
   - E.g., "FastAPI authentication pattern"
   - Store as structured recipes, not just text

5. **Parallelization Hints**
   - Analyzer detects parallel opportunities
   - Automatically parallelize independent todos
   - Store successful parallelization patterns

6. **Learning Graphs**
   - Connect related learnings
   - E.g., "FastAPI auth" → "JWT tokens" → "Token refresh"
   - Enable graph-based retrieval

7. **Selective Forgetting**
   - Prune low-value learnings periodically
   - Keep only high-confidence, frequently-accessed memories
   - Prevent database bloat

---

## Debugging & Monitoring

### Logging

**Learning submission**:
```python
logger.info(
    f"Submitted conversation for learning: "
    f"{len(messages)} messages, "
    f"{len(completed_tasks)}/{len(todos)} tasks completed, "
    f"delay={delay_seconds}s"
)
```

**Learning storage**:
```python
logger.info(
    f"Stored deep learning memory: {memory_id} - {memory['task']} "
    f"(confidence: {learning_result.confidence_score:.2f})"
)
```

**Skip decisions**:
```python
logger.info("Skipping learning: no relevance signals detected")
logger.info("Skipping learning: model flagged should_save=False (reason)")
```

### API Endpoints

**Get recent memories**:
```bash
GET http://localhost:8001/memories?limit=20
```

**Search memories**:
```bash
GET http://localhost:8001/memories/search?query=FastAPI&limit=5
```

**Get execution patterns**:
```bash
GET http://localhost:8001/patterns
```

### Database Queries

**Recent learnings**:
```sql
SELECT task, confidence_score, outcome, timestamp
FROM memories
ORDER BY timestamp DESC
LIMIT 20;
```

**High-confidence learnings**:
```sql
SELECT task, learnings, confidence_score
FROM memories
WHERE confidence_score > 0.8
ORDER BY confidence_score DESC;
```

**Learning statistics**:
```sql
SELECT
    COUNT(*) as total_memories,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE outcome = 'success') as successes,
    COUNT(*) FILTER (WHERE outcome = 'failure') as failures
FROM memories;
```
