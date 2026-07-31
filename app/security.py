from __future__ import annotations

import hmac
import ipaddress
from urllib.parse import urlsplit

from fastapi import Request

from .config import ACCESS_TOKEN
from .product import PRODUCT

# These are public protocol identifiers, not credential values.
TOKEN_COOKIE = f"{PRODUCT.slug.replace('-', '_')}_token"
TOKEN_HEADER = "X-Local-AI-Token"  # nosec B105


def token_matches(value: str | None) -> bool:
    return bool(
        ACCESS_TOKEN
        and value
        and hmac.compare_digest(value.encode(), ACCESS_TOKEN.encode())
    )


def request_is_loopback(request: Request) -> bool:
    if request.client is None:
        return False
    try:
        return ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        return False


def request_is_authorized(request: Request) -> bool:
    return token_matches(request.cookies.get(TOKEN_COOKIE)) or token_matches(
        request.headers.get(TOKEN_HEADER)
    )


def origin_is_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin or origin == "null":
        return True
    parsed = urlsplit(origin)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {
        "127.0.0.1",
        "localhost",
    }
