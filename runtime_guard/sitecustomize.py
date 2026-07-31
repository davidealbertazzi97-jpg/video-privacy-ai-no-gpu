"""Deny non-loopback network connections in Python application processes."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_create_connection = socket.create_connection
_original_getaddrinfo = socket.getaddrinfo
_original_bind = socket.socket.bind
_original_sendto = socket.socket.sendto
_original_sendmsg = getattr(socket.socket, "sendmsg", None)


def _host_is_local(host: Any) -> bool:
    if host == "localhost":
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="ignore")
    if not isinstance(host, str):
        return False
    host = host.removeprefix("[").removesuffix("]")
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.casefold() == "localhost"


def _address_is_local(address: Any) -> bool:
    if isinstance(address, tuple) and address:
        return _host_is_local(address[0])
    # Unix-domain sockets and other platform-local address forms are allowed.
    return not isinstance(address, tuple)


def _deny(address: Any) -> None:
    if not _address_is_local(address):
        raise PermissionError(
            "Local AI App Starter blocked a non-loopback network connection."
        )


def guarded_connect(self: socket.socket, address: Any) -> None:
    _deny(address)
    return _original_connect(self, address)


def guarded_connect_ex(self: socket.socket, address: Any) -> int:
    try:
        _deny(address)
    except PermissionError:
        return 13
    return _original_connect_ex(self, address)


def guarded_create_connection(
    address: Any,
    timeout: object = socket._GLOBAL_DEFAULT_TIMEOUT,
    source_address: Any = None,
    *,
    all_errors: bool = False,
) -> socket.socket:
    _deny(address)
    return _original_create_connection(
        address,
        timeout,
        source_address,
        all_errors=all_errors,
    )


def guarded_getaddrinfo(
    host: Any,
    port: Any,
    family: int = 0,
    type: int = 0,
    proto: int = 0,
    flags: int = 0,
):
    if not _host_is_local(host):
        raise socket.gaierror(
            socket.EAI_NONAME,
            "Only loopback names and addresses are allowed.",
        )
    return _original_getaddrinfo(host, port, family, type, proto, flags)


def guarded_bind(self: socket.socket, address: Any) -> None:
    _deny(address)
    return _original_bind(self, address)


def guarded_sendto(self: socket.socket, data: bytes, *args: Any) -> int:
    if not args:
        raise TypeError("sendto expected a destination address")
    _deny(args[-1])
    return _original_sendto(self, data, *args)


def guarded_sendmsg(
    self: socket.socket,
    buffers: Any,
    ancdata: Any = (),
    flags: int = 0,
    address: Any = None,
) -> int:
    if address is not None:
        _deny(address)
    if _original_sendmsg is None:
        raise AttributeError("sendmsg is unavailable on this platform")
    if address is None:
        return _original_sendmsg(self, buffers, ancdata, flags)
    return _original_sendmsg(self, buffers, ancdata, flags, address)


socket.socket.connect = guarded_connect
socket.socket.connect_ex = guarded_connect_ex
socket.create_connection = guarded_create_connection
socket.getaddrinfo = guarded_getaddrinfo
socket.socket.bind = guarded_bind
socket.socket.sendto = guarded_sendto
if _original_sendmsg is not None:
    socket.socket.sendmsg = guarded_sendmsg
