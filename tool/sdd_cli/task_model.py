"""Task-Datenmodell für SPEC-0026 – LLM Task Distribution Engine.

Kanonische Datenstruktur gemäß CON-0096.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    REVIEW = "review"
    PASSED = "passed"
    FAILED = "failed"
    COMMITTED = "committed"
    RETRYING = "retrying"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    CODE = "code"
    TEST = "test"
    CONFIG = "config"
    DOC = "doc"


class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContextSize(str, Enum):
    S = "S"
    M = "M"
    L = "L"


@dataclass
class Task:
    spec_id: str
    title: str
    description: str
    type: TaskType
    complexity: Complexity
    context_size: ContextSize
    estimated_tokens: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    llm_id: str | None = None
    container_id: str | None = None
    commit_hash: str | None = None
    dependencies: list[str] = field(default_factory=list)
    error_context: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "complexity": self.complexity.value,
            "context_size": self.context_size.value,
            "estimated_tokens": self.estimated_tokens,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "llm_id": self.llm_id,
            "container_id": self.container_id,
            "commit_hash": self.commit_hash,
            "dependencies": self.dependencies,
            "error_context": self.error_context,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            id=d["id"],
            spec_id=d["spec_id"],
            title=d["title"],
            description=d["description"],
            type=TaskType(d["type"]),
            complexity=Complexity(d["complexity"]),
            context_size=ContextSize(d["context_size"]),
            estimated_tokens=d["estimated_tokens"],
            status=TaskStatus(d["status"]),
            retry_count=d["retry_count"],
            llm_id=d.get("llm_id"),
            container_id=d.get("container_id"),
            commit_hash=d.get("commit_hash"),
            dependencies=d.get("dependencies", []),
            error_context=d.get("error_context", []),
        )
