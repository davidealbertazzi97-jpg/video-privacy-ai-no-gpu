from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EngineResult:
    summary: dict[str, Any]
    artifacts: tuple[Path, ...]


class LocalEngine(ABC):
    engine_id: str
    label_en: str
    label_it: str
    description_en: str
    description_it: str
    accepted_extensions: frozenset[str]

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.engine_id,
            "label_en": self.label_en,
            "label_it": self.label_it,
            "description_en": self.description_en,
            "description_it": self.description_it,
            "accepted_extensions": sorted(self.accepted_extensions),
        }

    def accepts(self, path: Path) -> bool:
        return path.suffix.casefold() in self.accepted_extensions

    @abstractmethod
    def process(
        self,
        source: Path,
        output_dir: Path,
        options: dict[str, Any],
    ) -> EngineResult:
        """Process one private local file and return non-sensitive metadata."""
