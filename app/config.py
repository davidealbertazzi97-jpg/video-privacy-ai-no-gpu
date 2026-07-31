from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .product import APP_ROOT, PRODUCT


def _platform_roots() -> tuple[Path, Path, Path]:
    home = Path.home()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        data = local / PRODUCT.name
        state = data / "state"
    elif sys.platform == "darwin":
        data = home / "Library" / "Application Support" / PRODUCT.name
        state = home / "Library" / "Caches" / PRODUCT.name
    else:
        data_home = Path(
            os.environ.get("XDG_DATA_HOME", home / ".local" / "share")
        ).expanduser()
        state_home = Path(
            os.environ.get("XDG_STATE_HOME", home / ".local" / "state")
        ).expanduser()
        data = data_home / PRODUCT.slug
        state = state_home / PRODUCT.slug

    documents = home / "Documents"
    if not documents.is_dir() and (home / "Documenti").is_dir():
        documents = home / "Documenti"
    return data, state, documents / f"{PRODUCT.name} - Results"


def _private_directory(path: Path) -> None:
    existed = path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt" and not existed:
        path.chmod(0o700)


@dataclass(frozen=True)
class Paths:
    app: Path
    data: Path
    work: Path
    outputs: Path
    state: Path
    database: Path

    @classmethod
    def build(cls) -> Paths:
        default_data, default_state, default_outputs = _platform_roots()
        prefix = PRODUCT.slug.upper().replace("-", "_")
        data = Path(os.environ.get(f"{prefix}_DATA", default_data)).expanduser()
        state = Path(os.environ.get(f"{prefix}_STATE", default_state)).expanduser()
        outputs = Path(
            os.environ.get(f"{prefix}_OUTPUTS", default_outputs)
        ).expanduser()
        paths = cls(
            app=APP_ROOT,
            data=data,
            work=data / "work",
            outputs=outputs,
            state=state,
            database=data / "jobs.sqlite3",
        )
        for directory in (paths.data, paths.work, paths.outputs, paths.state):
            _private_directory(directory)
        return paths


PATHS = Paths.build()
ACCESS_TOKEN = os.environ.get("LOCAL_AI_APP_TOKEN", "")
HOST = "127.0.0.1"
PORT = int(os.environ.get("LOCAL_AI_APP_PORT", "8765"))
MAX_UPLOAD_BYTES = int(
    os.environ.get("LOCAL_AI_APP_MAX_UPLOAD_BYTES", str(2048 * 1024**2))
)
