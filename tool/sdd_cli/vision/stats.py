from __future__ import annotations

from dataclasses import dataclass

from .document import VisionDocument


@dataclass(frozen=True)
class VisionStats:
    feature_count: int
    task_total: int
    task_done: int
    task_open: int
    llm_challenge_count: int
    code_challenge_count: int

    def __post_init__(self) -> None:
        for field in (
            "feature_count", "task_total", "task_done", "task_open",
            "llm_challenge_count", "code_challenge_count",
        ):
            if getattr(self, field) < 0:
                raise ValueError(f"{field} must be >= 0")
        if self.task_done + self.task_open != self.task_total:
            raise ValueError(
                f"task_done ({self.task_done}) + task_open ({self.task_open}) "
                f"!= task_total ({self.task_total})"
            )
        if self.llm_challenge_count > self.feature_count:
            raise ValueError("llm_challenge_count must not exceed feature_count")
        if self.code_challenge_count > self.feature_count:
            raise ValueError("code_challenge_count must not exceed feature_count")

    @classmethod
    def from_document(cls, doc: VisionDocument) -> "VisionStats":
        features = doc.features or []
        tasks = doc.tasks or []
        task_done = sum(1 for t in tasks if t.done)
        return cls(
            feature_count=len(features),
            task_total=len(tasks),
            task_done=task_done,
            task_open=len(tasks) - task_done,
            llm_challenge_count=sum(1 for f in features if f.llm_challenge is not None),
            code_challenge_count=sum(1 for f in features if f.code_challenge is not None),
        )
