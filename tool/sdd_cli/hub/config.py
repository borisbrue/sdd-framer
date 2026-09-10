from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class HubConfig(BaseModel):
    port: int = 4711

    @classmethod
    def load(cls, path: Path | None = None) -> HubConfig:
        cfg_path = path or Path.home() / ".config" / "sdd" / "hub.yaml"
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            hub_section = data.get("hub", data)
            return cls(**{k: v for k, v in hub_section.items() if k in cls.model_fields})
        return cls()

    def save(self, path: Path | None = None) -> None:
        cfg_path = path or Path.home() / ".config" / "sdd" / "hub.yaml"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(yaml.dump({"hub": self.model_dump()}))
