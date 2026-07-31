#!/usr/bin/env python3
"""Start the configured application with a private loopback-only launcher."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8765
sys.path.insert(0, str(APP_DIR))
from app.product import PRODUCT  # noqa: E402


def config_root() -> Path:
    home = Path.home()
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return local / PRODUCT.name
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / PRODUCT.name
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")).expanduser()
    return xdg / PRODUCT.slug


def load_config() -> dict[str, Any]:
    root = config_root()
    root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        root.chmod(0o700)
    path = root / "launcher.json"
    values: dict[str, Any] = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                values = loaded
        except (OSError, ValueError):
            values = {}
    token = os.environ.get("LOCAL_AI_APP_TOKEN") or values.get("token")
    if not isinstance(token, str) or len(token) < 48:
        token = secrets.token_urlsafe(48)
    env_port = os.environ.get("LOCAL_AI_APP_PORT")
    if env_port and env_port.isdigit():
        port = int(env_port)
    else:
        port = values.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        port = DEFAULT_PORT
    clean = {"token": token, "port": port}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        temporary.chmod(0o600)
    os.replace(temporary, path)
    if os.name != "nt":
        path.chmod(0o600)
    return clean


def get_json(url: str, timeout: float = 1.0) -> dict[str, Any] | None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise ValueError("The launcher accepts numeric loopback HTTP endpoints only.")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec B310
            value = json.load(response)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def app_is_ready(port: int) -> bool:
    value = get_json(f"http://127.0.0.1:{port}/health")
    return value is not None and value.get("app") == PRODUCT.slug


def token_is_authorized(port: int, token: str) -> bool:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/product",
        headers={"X-Local-AI-Token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=1) as response:  # nosec B310
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def port_is_available(port: int) -> bool:
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def guarded_environment(token: str, port: int) -> dict[str, str]:
    environment = os.environ.copy()
    for variable in (
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "PYTHONBREAKPOINT",
        "PYTHONEXECUTABLE",
        "PYTHONHOME",
        "PYTHONINSPECT",
        "PYTHONPLATLIBDIR",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
        "PYTHONWARNINGS",
    ):
        environment.pop(variable, None)
    environment.update(
        {
            "LOCAL_AI_APP_TOKEN": token,
            "LOCAL_AI_APP_PORT": str(port),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": str(APP_DIR / "runtime_guard"),
        }
    )
    native_guard = APP_DIR / "bin" / "liblocal_ai_netguard.so"
    if sys.platform.startswith("linux") and native_guard.is_file():
        environment["LD_PRELOAD"] = str(native_guard)
    return environment


def open_app(port: int, token: str) -> None:
    url = f"http://127.0.0.1:{port}/?token={token}"
    if not webbrowser.open(url, new=1):
        print(f"Open in a browser: {url}")


def stop_process(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=12)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=f"Start {PRODUCT.name} locally.")
    root.add_argument("--no-browser", action="store_true")
    return root


def raise_keyboard_interrupt() -> None:
    raise KeyboardInterrupt


def main() -> int:
    args = parser().parse_args()
    config = load_config()
    token = str(config["token"])
    port = int(config["port"])
    if app_is_ready(port) and token_is_authorized(port, token):
        if not args.no_browser:
            open_app(port, token)
        print(f"{PRODUCT.name} is already active on http://127.0.0.1:{port}/")
        return 0
    if not port_is_available(port):
        port = free_port()
        config["port"] = port
        path = config_root() / "launcher.json"
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        if os.name != "nt":
            path.chmod(0o600)

    environment = guarded_environment(token, port)
    log_path = config_root() / "server.log"
    log_path.touch(exist_ok=True)
    if os.name != "nt":
        log_path.chmod(0o600)
    with log_path.open("ab") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            cwd=APP_DIR,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(120):
                if server.poll() is not None:
                    detail = log_path.read_text(encoding="utf-8", errors="replace")
                    raise RuntimeError(
                        f"{PRODUCT.name} did not start:\n{detail[-3000:]}"
                    )
                if app_is_ready(port):
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError(f"Timed out while starting {PRODUCT.name}.")
            if not args.no_browser:
                open_app(port, token)
            print(
                f"{PRODUCT.name} is active on http://127.0.0.1:{port}/\n"
                "Press Ctrl+C to stop it."
            )
            server.wait()
        except KeyboardInterrupt:
            print(f"\nStopping {PRODUCT.name}...")
        finally:
            stop_process(server)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: raise_keyboard_interrupt())
    raise SystemExit(main())
