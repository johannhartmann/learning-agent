"""Models for orchestration."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TodoStatus(str, Enum):
    """Status of a todo item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TodoItem(BaseModel):
    """Represents a single todo item."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    status: TodoStatus = TodoStatus.PENDING
    priority: int = Field(ge=0, le=10, default=5)
    dependencies: list[str] = Field(default_factory=list)
    assigned_agent: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
