"""API server for learning agent with memory fetching endpoint."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
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


@app.get("/api/files/{file_path:path}")
async def get_file(file_path: str, thread_id: str | None = None) -> Response:
    """Retrieve a file from the session state via LangGraph API.

    Args:
        file_path: Path to the file in the virtual filesystem
        thread_id: Optional thread ID to fetch state from (for session isolation)

    Returns:
        File content with appropriate content type
    """
    import base64

    import httpx  # type: ignore[import-not-found]

    # Normalize the path
    normalized_path = file_path if file_path.startswith("/") else f"/{file_path}"

    # Try to fetch from LangGraph server state if thread_id is provided
    if thread_id:
        try:
            # Connect to LangGraph server API to get thread state
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"http://localhost:2024/threads/{thread_id}/state",
                    headers={
                        "Content-Type": "application/json",
                        "X-Api-Key": "test-key",
                    },
                )

                if response.status_code == 200:
                    state_data = response.json()
                    # Get files from the state
                    files = state_data.get("values", {}).get("files", {})

                    # Try different path variations
                    path_variations = [
                        normalized_path,
                        file_path,
                        f"/sandbox/{file_path}"
                        if not file_path.startswith("/sandbox")
                        else file_path,
                    ]

                    for path in path_variations:
                        if path in files:
                            # Decode base64 content
                            file_content = base64.b64decode(files[path])

                            # Determine content type based on file extension
                            if path.endswith(".png"):
                                media_type = "image/png"
                            elif path.endswith((".jpg", ".jpeg")):
                                media_type = "image/jpeg"
                            elif path.endswith(".svg"):
                                media_type = "image/svg+xml"
                            elif path.endswith(".json"):
                                media_type = "application/json"
                            else:
                                media_type = "application/octet-stream"

                            return Response(
                                content=file_content,
                                media_type=media_type,
                                headers={"Cache-Control": "no-cache"},  # Don't cache session data
                            )
        except Exception:
            logger.exception("Error fetching file from thread state")

    # If file is a plot but not found, return a placeholder
    if "plots" in file_path:
        # Generate a simple placeholder SVG image (no PIL dependency needed)
        filename = file_path.split("/")[-1]
        svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="300" fill="white" stroke="gray" stroke-width="2"/>
  <text x="200" y="150" text-anchor="middle" font-family="Arial" font-size="16" fill="black">
    Plot: {filename}
  </text>
  <text x="200" y="180" text-anchor="middle" font-family="Arial" font-size="12" fill="gray">
    (Session file not found - ensure thread_id is provided)
  </text>
</svg>"""

        return Response(
            content=svg_content.encode("utf-8"),
            media_type="image/svg+xml",
            headers={"Cache-Control": "no-cache"},
        )

    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


if __name__ == "__main__":
    import os

    import uvicorn

    # In Docker, bind to all interfaces; locally bind to localhost
    host = "0.0.0.0" if os.environ.get("DOCKER_ENV") else "127.0.0.1"  # nosec B104
    uvicorn.run(app, host=host, port=8001)
