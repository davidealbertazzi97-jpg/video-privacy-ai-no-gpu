from __future__ import annotations

import json
import os
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any

from .config import PATHS


def safe_name(name: str, fallback: str = "document") -> str:
    name = Path(name.replace("\\", "/")).name
    normalized = unicodedata.normalize("NFKC", name)
    normalized = re.sub(r"[\x00-\x1f\x7f/\\]+", "_", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .")
    if not normalized or normalized in {".", ".."}:
        return fallback
    windows_reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
    if normalized.split(".", 1)[0].upper() in windows_reserved:
        normalized = f"_{normalized}"
    return normalized[:180]


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def remove_work_tree(path: Path) -> None:
    resolved = path.resolve()
    work = PATHS.work.resolve()
    if resolved != work and work in resolved.parents:
        shutil.rmtree(resolved, ignore_errors=True)


def resolve_artifact(root: Path, relative_name: str) -> Path:
    relative = Path(relative_name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("invalid artifact path")
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if resolved_root not in candidate.parents or not candidate.is_file():
        raise ValueError("artifact not found")
    return candidate
