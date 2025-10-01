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

            # Historical tables for patterns/queues have been removed; memories only.

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
