"""PostgreSQL with pgvector storage backend for deep learning system memories."""

import json
import os
from datetime import datetime
from typing import Any
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped, unused-ignore]
import numpy as np
from langchain_openai import OpenAIEmbeddings
from pgvector.asyncpg import register_vector  # type: ignore[import-untyped, unused-ignore]


class VectorLearningStorage:
    """PostgreSQL + pgvector storage for deep learned memories with multi-dimensional insights."""

    def __init__(self, database_url: str | None = None):
        """Initialize the vector learning storage."""
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://learning_agent:learning_agent_pass@localhost:5433/learning_memories",
        )
        self.pool: asyncpg.Pool | None = None  # type: ignore[no-any-unimported, unused-ignore]
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    async def initialize(self) -> None:
        """Initialize the database connection pool and create enhanced tables."""
        self.pool = await asyncpg.create_pool(self.database_url)

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            # Create pgvector extension first
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Then register pgvector type
            await register_vector(conn)

            # Create enhanced memories table with deep learning fields (IF NOT EXISTS)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task TEXT NOT NULL,
                    context TEXT,
                    narrative TEXT,

                    -- Basic reflection
                    reflection TEXT,

                    -- Deep learning dimensions
                    tactical_learning TEXT,  -- Specific implementation insights
                    strategic_learning TEXT,  -- Higher-level patterns and approaches
                    meta_learning TEXT,  -- Learning about the learning process itself

                    -- Anti-patterns and inefficiencies
                    anti_patterns JSONB,  -- What NOT to do, inefficiencies found

                    -- Execution analysis
                    execution_metadata JSONB,  -- Tool usage, redundancies, parallelization
                    confidence_score FLOAT DEFAULT 0.5,

                    outcome TEXT,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB,

                    -- Embeddings
                    embedding vector(1536),  -- General content embedding
                    task_embedding vector(1536)  -- Task-specific embedding
                )
            """)

            # Create indexes for vector similarity search
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_embedding_idx
                ON memories USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS memories_task_embedding_idx
                ON memories USING ivfflat (task_embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

            # Create enhanced patterns table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    pattern TEXT NOT NULL,
                    pattern_type TEXT,  -- 'tool_sequence', 'strategy', 'anti_pattern', 'optimization'
                    description TEXT,
                    confidence FLOAT DEFAULT 0.0,
                    success_rate FLOAT DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_applied TIMESTAMPTZ,
                    metadata JSONB,
                    embedding vector(1536),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Create index for patterns
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS patterns_embedding_idx
                ON patterns USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 50)
            """)

            # Create learning queue table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_queue (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    task TEXT,
                    context TEXT,
                    outcome TEXT,
                    duration FLOAT,
                    description TEXT,
                    error TEXT,
                    execution_data JSONB,  -- Full execution trace for analysis
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    processed BOOLEAN DEFAULT FALSE,
                    priority INTEGER DEFAULT 0
                )
            """)

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()

    async def store_memory(self, memory: dict[str, Any]) -> str:
        """Store a deep learning memory with multi-dimensional insights."""
        if not self.pool:
            await self.initialize()

        # Generate SEPARATE embeddings
        # Task embedding - for finding similar tasks
        task_text = memory.get("task", "")
        task_embedding = await self.embeddings.aembed_query(task_text) if task_text else None

        # Content embedding - combines all learning dimensions
        text_for_embedding = " ".join(
            filter(
                None,
                [
                    memory.get("task", ""),
                    memory.get("reflection", ""),
                    memory.get("tactical_learning", ""),
                    memory.get("strategic_learning", ""),
                    memory.get("meta_learning", ""),
                ],
            )
        )
        embedding = await self.embeddings.aembed_query(text_for_embedding)

        memory_id = memory.get("id") or str(uuid4())

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute(
                """
                INSERT INTO memories (
                    id, task, context, narrative, reflection,
                    tactical_learning, strategic_learning, meta_learning,
                    anti_patterns, execution_metadata, confidence_score,
                    outcome, timestamp, metadata, embedding, task_embedding
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (id) DO UPDATE SET
                    task = EXCLUDED.task,
                    context = EXCLUDED.context,
                    narrative = EXCLUDED.narrative,
                    reflection = EXCLUDED.reflection,
                    tactical_learning = EXCLUDED.tactical_learning,
                    strategic_learning = EXCLUDED.strategic_learning,
                    meta_learning = EXCLUDED.meta_learning,
                    anti_patterns = EXCLUDED.anti_patterns,
                    execution_metadata = EXCLUDED.execution_metadata,
                    confidence_score = EXCLUDED.confidence_score,
                    outcome = EXCLUDED.outcome,
                    timestamp = EXCLUDED.timestamp,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding,
                    task_embedding = EXCLUDED.task_embedding
            """,
                memory_id,
                memory.get("task"),
                memory.get("context"),
                memory.get("narrative"),
                memory.get("reflection"),
                memory.get("tactical_learning"),
                memory.get("strategic_learning"),
                memory.get("meta_learning"),
                json.dumps(memory.get("anti_patterns", {})),
                json.dumps(memory.get("execution_metadata", {})),
                memory.get("confidence_score", 0.5),
                memory.get("outcome"),
                memory.get("timestamp", datetime.now()),
                json.dumps(memory.get("metadata", {})),
                np.array(embedding),
                np.array(task_embedding) if task_embedding else None,
            )

        return memory_id

    async def search_similar_tasks(self, current_task: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for similar tasks and return their deep learnings.

        Args:
            current_task: The task to find similar past tasks for
            limit: Maximum number of similar tasks to return

        Returns:
            List of dictionaries containing similar tasks with all learning dimensions
        """
        if not self.pool:
            await self.initialize()

        # Generate embedding for the current task
        task_embedding = await self.embeddings.aembed_query(current_task)

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            # Register vector type for this connection
            await register_vector(conn)

            # Search using task similarity ONLY
            rows = await conn.fetch(
                """
                SELECT
                    id, task, reflection,
                    tactical_learning, strategic_learning, meta_learning,
                    anti_patterns, execution_metadata, confidence_score,
                    outcome, context, timestamp, metadata,
                    1 - (task_embedding <=> $1::vector) as similarity
                FROM memories
                WHERE task_embedding IS NOT NULL
                ORDER BY task_embedding <=> $1::vector
                LIMIT $2
            """,
                np.array(task_embedding),
                limit,
            )

            learnings = []
            for row in rows:
                learning = {
                    "id": str(row["id"]),
                    "similar_task": row["task"],
                    "learning": row["reflection"],  # Basic learning
                    "tactical_learning": row["tactical_learning"],
                    "strategic_learning": row["strategic_learning"],
                    "meta_learning": row["meta_learning"],
                    "anti_patterns": (
                        json.loads(row["anti_patterns"]) if row["anti_patterns"] else []
                    ),
                    "execution_metadata": (
                        json.loads(row["execution_metadata"]) if row["execution_metadata"] else {}
                    ),
                    "confidence_score": float(row["confidence_score"])
                    if row["confidence_score"]
                    else 0.5,
                    "outcome": row["outcome"],
                    "context": row["context"],
                    "similarity": float(row["similarity"]),
                    "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
                learnings.append(learning)

            return learnings

    async def search_similar_memories(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for memories similar to the query using vector similarity."""
        if not self.pool:
            await self.initialize()

        # Generate embedding for the query
        query_embedding = await self.embeddings.aembed_query(query)

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            # Register vector type for this connection
            await register_vector(conn)

            # Search using cosine similarity
            rows = await conn.fetch(
                """
                SELECT
                    id, task, context, narrative, reflection,
                    tactical_learning, strategic_learning, meta_learning,
                    anti_patterns, execution_metadata, confidence_score,
                    outcome, timestamp, metadata,
                    1 - (embedding <=> $1::vector) as similarity
                FROM memories
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """,
                np.array(query_embedding),
                limit,
            )

            memories = []
            for row in rows:
                memory = dict(row)
                memory["id"] = str(memory["id"])
                memory["timestamp"] = (
                    memory["timestamp"].isoformat() if memory["timestamp"] else None
                )
                memory["metadata"] = json.loads(memory["metadata"]) if memory["metadata"] else {}
                memory["anti_patterns"] = (
                    json.loads(memory["anti_patterns"]) if memory["anti_patterns"] else {}
                )
                memory["execution_metadata"] = (
                    json.loads(memory["execution_metadata"]) if memory["execution_metadata"] else {}
                )
                memories.append(memory)

            return memories

    async def get_recent_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent memories with all deep learning fields."""
        if not self.pool:
            await self.initialize()

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                """
                SELECT id, task, context, narrative, reflection,
                       tactical_learning, strategic_learning, meta_learning,
                       anti_patterns, execution_metadata, confidence_score,
                       outcome, timestamp, metadata
                FROM memories
                ORDER BY timestamp DESC
                LIMIT $1
            """,
                limit,
            )

            memories = []
            for row in rows:
                memory = dict(row)
                memory["id"] = str(memory["id"])
                memory["timestamp"] = (
                    memory["timestamp"].isoformat() if memory["timestamp"] else None
                )
                memory["metadata"] = json.loads(memory["metadata"]) if memory["metadata"] else {}
                memory["anti_patterns"] = (
                    json.loads(memory["anti_patterns"]) if memory["anti_patterns"] else {}
                )
                memory["execution_metadata"] = (
                    json.loads(memory["execution_metadata"]) if memory["execution_metadata"] else {}
                )
                memories.append(memory)

            return memories

    async def store_pattern(self, pattern: dict[str, Any]) -> str:
        """Store an extracted pattern with enhanced metadata."""
        if not self.pool:
            await self.initialize()

        # Generate embedding for the pattern
        pattern_text = f"{pattern.get('pattern', '')} {pattern.get('description', '')}"
        embedding = await self.embeddings.aembed_query(pattern_text)

        pattern_id = pattern.get("id") or str(uuid4())

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute(
                """
                INSERT INTO patterns (
                    id, pattern, pattern_type, description,
                    confidence, success_rate, usage_count,
                    success_count, failure_count, last_applied,
                    metadata, embedding
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    pattern = EXCLUDED.pattern,
                    pattern_type = EXCLUDED.pattern_type,
                    description = EXCLUDED.description,
                    confidence = EXCLUDED.confidence,
                    success_rate = EXCLUDED.success_rate,
                    usage_count = EXCLUDED.usage_count,
                    success_count = EXCLUDED.success_count,
                    failure_count = EXCLUDED.failure_count,
                    last_applied = EXCLUDED.last_applied,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding
            """,
                pattern_id,
                pattern.get("pattern"),
                pattern.get("pattern_type"),
                pattern.get("description"),
                pattern.get("confidence", 0.0),
                pattern.get("success_rate", 0.0),
                pattern.get("usage_count", 0),
                pattern.get("success_count", 0),
                pattern.get("failure_count", 0),
                pattern.get("last_applied"),
                json.dumps(pattern.get("metadata", {})),
                np.array(embedding),
            )

        return pattern_id

    async def get_patterns(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get patterns from storage with enhanced fields."""
        if not self.pool:
            await self.initialize()

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                """
                SELECT id, pattern, pattern_type, description,
                       confidence, success_rate, usage_count,
                       success_count, failure_count, last_applied, metadata
                FROM patterns
                ORDER BY confidence DESC, success_rate DESC
                LIMIT $1
            """,
                limit,
            )

            patterns = []
            for row in rows:
                pattern = dict(row)
                pattern["id"] = str(pattern["id"])
                pattern["last_applied"] = (
                    pattern["last_applied"].isoformat() if pattern["last_applied"] else None
                )
                pattern["metadata"] = json.loads(pattern["metadata"]) if pattern["metadata"] else {}
                patterns.append(pattern)

            return patterns

    async def queue_learning(self, learning_data: dict[str, Any]) -> str:
        """Queue learning data for processing with execution traces."""
        if not self.pool:
            await self.initialize()

        queue_id = str(uuid4())

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute(
                """
                INSERT INTO learning_queue (
                    id, task, context, outcome, duration,
                    description, error, execution_data,
                    priority, timestamp
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                queue_id,
                learning_data.get("task"),
                learning_data.get("context"),
                learning_data.get("outcome"),
                learning_data.get("duration"),
                learning_data.get("description"),
                learning_data.get("error"),
                json.dumps(learning_data.get("execution_data", {})),
                learning_data.get("priority", 0),
                datetime.now(),
            )

        return queue_id

    async def get_learning_queue(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get unprocessed items from learning queue."""
        if not self.pool:
            await self.initialize()

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch(
                """
                SELECT id, task, context, outcome, duration,
                       description, error, execution_data, priority, timestamp
                FROM learning_queue
                WHERE processed = FALSE
                ORDER BY priority DESC, timestamp DESC
                LIMIT $1
            """,
                limit,
            )

            queue_items = []
            for row in rows:
                item = dict(row)
                item["id"] = str(item["id"])
                item["execution_data"] = (
                    json.loads(item["execution_data"]) if item["execution_data"] else {}
                )
                item["timestamp"] = item["timestamp"].isoformat() if item["timestamp"] else None
                queue_items.append(item)

            return queue_items
