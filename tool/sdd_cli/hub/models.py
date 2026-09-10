from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ProjectEntry(BaseModel):
    id: str
    name: str
    path: Path
    start_cmd: list[str]
    port: int
    status: Literal["running", "stopped", "error"] = "stopped"
    pid: int | None = None
    last_started: datetime | None = None


class StatusEvent(BaseModel):
    id: str
    status: Literal["running", "stopped", "error"]
    pid: int | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
