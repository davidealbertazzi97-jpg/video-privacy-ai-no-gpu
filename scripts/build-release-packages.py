#!/usr/bin/env python3
"""Build release distribution packages for Linux, macOS, and Windows."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = APP_DIR / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

VERSION = "1.0.0"
APP_NAME = "Video-Privacy-Studio"

IGNORED_NAMES = {
    "__pycache__",
    ".DS_Store",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "Thumbs.db",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}

# Files to include in cross-platform release archives
RELEASE_FILES = [
    "app",
    "runtime_guard",
    "scripts",
    "static",
    "tests",
    "install.ps1",
    "install.sh",
    "LICENSE",
    "NOTICE",
    "product.toml",
    "pyproject.toml",
    "README.md",
    "requirements-core.txt",
    "SECURITY.md",
    "start.ps1",
    "start.sh",
]


def should_exclude(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or (
        path.suffix.lower() in IGNORED_SUFFIXES
    )


def clean_tar_entry(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    return None if should_exclude(Path(info.name)) else info


def create_tar_release(name: str, target_tar: Path) -> None:
    print(f"Building {target_tar.name}...")
    with tarfile.open(target_tar, "w:gz") as tar:
        for rel in RELEASE_FILES:
            path = APP_DIR / rel
            if path.exists():
                tar.add(path, arcname=f"{name}/{rel}", filter=clean_tar_entry)
    print(f"Created {target_tar.name} ({target_tar.stat().st_size} bytes)")


def create_zip_release(name: str, target_zip: Path) -> None:
    print(f"Building {target_zip.name}...")
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for rel in RELEASE_FILES:
            path = APP_DIR / rel
            if path.is_file():
                zip_file.write(path, arcname=f"{name}/{rel}")
            elif path.is_dir():
                for sub in path.rglob("*"):
                    if sub.is_file() and not should_exclude(
                        sub.relative_to(APP_DIR)
                    ):
                        zip_file.write(
                            sub, arcname=f"{name}/{sub.relative_to(APP_DIR)}"
                        )
    print(f"Created {target_zip.name} ({target_zip.stat().st_size} bytes)")


def main() -> None:
    print("--- BUILDING VIDEO PRIVACY STUDIO RELEASE PACKAGES ---")

    linux_tar = DIST_DIR / f"{APP_NAME}-v{VERSION}-Linux-x86_64.tar.gz"
    macos_tar = DIST_DIR / f"{APP_NAME}-v{VERSION}-macOS-Universal.tar.gz"
    win_zip = DIST_DIR / f"{APP_NAME}-v{VERSION}-Windows-x64.zip"

    create_tar_release(f"{APP_NAME}-v{VERSION}", linux_tar)
    create_tar_release(f"{APP_NAME}-v{VERSION}", macos_tar)
    create_zip_release(f"{APP_NAME}-v{VERSION}", win_zip)

    print("\nAll release packages created successfully in `dist/`:")
    for p in DIST_DIR.iterdir():
        if p.is_file():
            size_mb = p.stat().st_size / (1024 * 1024)
            print(f" - {p.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
