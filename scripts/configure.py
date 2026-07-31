#!/usr/bin/env python3
"""Give a fresh starter copy its product identity."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PRODUCT_FILE = APP_DIR / "product.toml"
PYPROJECT_FILE = APP_DIR / "pyproject.toml"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){2}(?:[a-z0-9.-]+)?$")
UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Configure a copied starter project.")
    root.add_argument("--name", required=True)
    root.add_argument("--slug", required=True)
    root.add_argument("--description-en", required=True)
    root.add_argument("--description-it", required=True)
    root.add_argument("--language", choices=("en", "it"), default="it")
    root.add_argument("--version", default="0.1.0")
    return root


def main() -> int:
    args = parser().parse_args()
    if not SLUG.fullmatch(args.slug):
        raise SystemExit("Slug must use lowercase letters, digits, and hyphens.")
    name = args.name.strip()
    if (
        not name
        or UNSAFE_NAME.search(name)
        or name in {".", ".."}
        or name.endswith((".", " "))
    ):
        raise SystemExit("Name contains characters unsafe for a directory name.")
    if not VERSION.fullmatch(args.version):
        raise SystemExit("Version must look like 1.2.3 or 1.2.3rc1.")
    content = "\n".join(
        (
            "[product]",
            f"name = {quoted(name)}",
            f"slug = {quoted(args.slug)}",
            f"version = {quoted(args.version)}",
            f"description_en = {quoted(args.description_en.strip())}",
            f"description_it = {quoted(args.description_it.strip())}",
            f"default_language = {quoted(args.language)}",
            "",
        )
    )
    temporary = PRODUCT_FILE.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(PRODUCT_FILE)

    pyproject = PYPROJECT_FILE.read_text(encoding="utf-8")
    pyproject = re.sub(
        r'(?m)^name = "[^"]+"$',
        f'name = "{args.slug}"',
        pyproject,
        count=1,
    )
    pyproject = re.sub(
        r'(?m)^version = "[^"]+"$',
        f'version = "{args.version}"',
        pyproject,
        count=1,
    )
    pyproject_temporary = PYPROJECT_FILE.with_suffix(".tmp")
    pyproject_temporary.write_text(pyproject, encoding="utf-8")
    pyproject_temporary.replace(PYPROJECT_FILE)

    print(f"Configured {args.name} in {PRODUCT_FILE}")
    print("Now replace app/engines/example.py and update app/engines/__init__.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
