"""API server for learning agent with memory fetching endpoint."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from learning_agent.learning.langmem_integration import get_learning_system


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Learning Agent API", version="0.1.0")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:10300", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MemoryItem(BaseModel):
    """Model for individual memory with deep learning dimensions."""

    id: str
    task: str
    context: str | None = None
    narrative: str | None = None
    reflection: str | None = None
    tactical_learning: str | None = None
    strategic_learning: str | None = None
    meta_learning: str | None = None
    anti_patterns: dict[str, Any] | None = None
    execution_metadata: dict[str, Any] | None = None
    confidence_score: float = 0.5
    outcome: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] | None = None
    similarity: float | None = None


class PatternItem(BaseModel):
    """Model for pattern with enhanced metadata."""

    id: str
    pattern: str
    pattern_type: str | None = None
    description: str | None = None
    confidence: float = 0.0
    success_rate: float = 0.0
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_applied: str | None = None
    metadata: dict[str, Any] | None = None


class MemoriesResponse(BaseModel):
    """Response model for memories endpoint with full deep learning data."""

    memories: list[MemoryItem]
    patterns: list[PatternItem]
    learning_queue: list[dict[str, Any]]


@app.get("/api/memories", response_model=MemoriesResponse)
async def get_memories() -> MemoriesResponse:
    """Fetch processed memories with deep learning dimensions.

    Returns:
        MemoriesResponse containing memories with all learning fields, patterns, and learning queue
    """
    try:
        learning_system = get_learning_system()
        memories, patterns, learning_queue = await learning_system.get_processed_memories_for_ui()

        logger.info(
            f"Fetched {len(memories)} memories, "
            f"{len(patterns)} patterns, "
            f"{len(learning_queue)} queued items"
        )

        # Convert dictionaries to Pydantic models
        memory_items = [
            MemoryItem(
                id=memory.get("id", ""),
                task=memory.get("task", ""),
                context=memory.get("context"),
                narrative=memory.get("narrative"),
                reflection=memory.get("reflection"),
                tactical_learning=memory.get("tactical_learning"),
                strategic_learning=memory.get("strategic_learning"),
                meta_learning=memory.get("meta_learning"),
                anti_patterns=memory.get("anti_patterns"),
                execution_metadata=memory.get("execution_metadata"),
                confidence_score=memory.get("confidence_score", 0.5),
                outcome=memory.get("outcome"),
                timestamp=memory.get("timestamp"),
                metadata=memory.get("metadata"),
                similarity=memory.get("similarity"),
            )
            for memory in memories
        ]

        pattern_items = [
            PatternItem(
                id=pattern.get("id", ""),
                pattern=pattern.get("pattern", ""),
                pattern_type=pattern.get("pattern_type"),
                description=pattern.get("description"),
                confidence=pattern.get("confidence", 0.0),
                success_rate=pattern.get("success_rate", 0.0),
                usage_count=pattern.get("usage_count", 0),
                success_count=pattern.get("success_count", 0),
                failure_count=pattern.get("failure_count", 0),
                last_applied=pattern.get("last_applied"),
                metadata=pattern.get("metadata"),
            )
            for pattern in patterns
        ]

        return MemoriesResponse(
            memories=memory_items,
            patterns=pattern_items,
            learning_queue=learning_queue,
        )
    except Exception as e:
        logger.exception("Error fetching memories")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import os

    import uvicorn

    # In Docker, bind to all interfaces; locally bind to localhost
    host = "0.0.0.0" if os.environ.get("DOCKER_ENV") else "127.0.0.1"  # nosec B104
    uvicorn.run(app, host=host, port=8001)
