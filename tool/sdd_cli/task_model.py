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
    con_ids: list[str] = field(default_factory=list)
    # SPEC-0034: Kanban-Board fields
    parallel_group: str | None = None
    test_ids: list[str] = field(default_factory=list)
    actual_tokens: int | None = None
    run_id: str | None = None

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
            "con_ids": self.con_ids,
            "parallel_group": self.parallel_group,
            "test_ids": self.test_ids,
            "actual_tokens": self.actual_tokens,
            "run_id": self.run_id,
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
            con_ids=d.get("con_ids", []),
            parallel_group=d.get("parallel_group"),
            test_ids=d.get("test_ids", []),
            actual_tokens=d.get("actual_tokens"),
            run_id=d.get("run_id"),
        )
