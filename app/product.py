from __future__ import annotations

import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
PRODUCT_FILE = APP_ROOT / "product.toml"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNSAFE_PATH_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class Product:
    name: str
    slug: str
    version: str
    description_en: str
    description_it: str
    default_language: str

    def public_dict(self) -> dict[str, str]:
        return asdict(self)


def load_product(path: Path = PRODUCT_FILE) -> Product:
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    raw = document.get("product")
    if not isinstance(raw, dict):
        raise ValueError("product.toml must contain a [product] table")

    required = (
        "name",
        "slug",
        "version",
        "description_en",
        "description_it",
        "default_language",
    )
    values: dict[str, str] = {}
    for key in required:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"product.{key} must be a non-empty string")
        values[key] = value.strip()

    if not SLUG_PATTERN.fullmatch(values["slug"]):
        raise ValueError("product.slug must use lowercase letters, digits, and hyphens")
    if (
        UNSAFE_PATH_NAME.search(values["name"])
        or values["name"] in {".", ".."}
        or values["name"].endswith((".", " "))
    ):
        raise ValueError("product.name contains characters unsafe for a directory name")
    if values["default_language"] not in {"it", "en"}:
        raise ValueError("product.default_language must be 'it' or 'en'")
    return Product(**values)


PRODUCT = load_product()
