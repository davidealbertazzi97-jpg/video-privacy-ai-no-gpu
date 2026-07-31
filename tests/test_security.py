from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent


class RuntimeNetworkGuardTests(unittest.TestCase):
    def run_guarded(self, code: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(APP_DIR / "runtime_guard")
        environment.pop("LD_PRELOAD", None)
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=APP_DIR,
            env=environment,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_external_name_resolution_is_denied(self) -> None:
        result = self.run_guarded(
            "import socket\n"
            "try:\n"
            " socket.getaddrinfo('example.com', 443)\n"
            "except socket.gaierror:\n"
            " raise SystemExit(0)\n"
            "raise SystemExit(3)\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_numeric_loopback_is_allowed(self) -> None:
        result = self.run_guarded(
            "import socket\n"
            "value=socket.getaddrinfo('127.0.0.1', 8765)\n"
            "raise SystemExit(0 if value else 4)\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_external_udp_destination_is_denied(self) -> None:
        result = self.run_guarded(
            "import socket\n"
            "sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
            "try:\n"
            " sock.sendto(b'x', ('192.0.2.1', 9))\n"
            "except PermissionError:\n"
            " raise SystemExit(0)\n"
            "raise SystemExit(5)\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wildcard_listener_is_denied(self) -> None:
        result = self.run_guarded(
            "import socket\n"
            "sock=socket.socket()\n"
            "try:\n"
            " sock.bind(('0.0.0.0', 0))\n"
            "except PermissionError:\n"
            " raise SystemExit(0)\n"
            "raise SystemExit(6)\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
