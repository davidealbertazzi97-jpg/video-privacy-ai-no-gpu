#!/usr/bin/env python3
"""Exercise loopback server and video redaction job for Video Privacy Studio."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))
TOKEN = "smoke-test-" + "x" * 48


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request_json(
    url: str,
    *,
    token: bool = False,
    data: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, object]:
    headers = {}
    if token:
        headers["X-Local-AI-Token"] = TOKEN
    if data is not None:
        parsed = urllib.parse.urlsplit(url)
        headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_body = json.loads(body)
        except ValueError:
            parsed_body = body
        return exc.code, parsed_body


def create_sample_video(path: Path) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, 10.0, (160, 120))
    for _i in range(10):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        cv2.circle(frame, (80, 60), 30, (255, 255, 255), -1)
        out.write(frame)
    out.release()


def main() -> None:
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="video-privacy-smoke-") as temporary:
        root = Path(temporary)
        env = os.environ.copy()
        env.update(
            {
                "VIDEO_PRIVACY_STUDIO_DATA": str(root / "data"),
                "VIDEO_PRIVACY_STUDIO_STATE": str(root / "state"),
                "VIDEO_PRIVACY_STUDIO_OUTPUTS": str(root / "outputs"),
                "LOCAL_AI_APP_TOKEN": TOKEN,
                "LOCAL_AI_APP_PORT": str(port),
                "PYTHONUNBUFFERED": "1",
            }
        )

        server = subprocess.Popen(
            [sys.executable, str(APP_DIR / "scripts" / "start.py"), "--no-browser"],
            cwd=APP_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            endpoint = f"http://127.0.0.1:{port}"
            ready = False
            for _ in range(50):
                try:
                    status, payload = request_json(f"{endpoint}/health")
                    if (
                        status == 200
                        and isinstance(payload, dict)
                        and payload.get("status") == "ok"
                    ):
                        ready = True
                        break
                except Exception:
                    pass
                time.sleep(0.1)

            if not ready:
                raise RuntimeError("Server did not report health OK in time")

            # Check Product & Engines
            status, prod = request_json(f"{endpoint}/api/product", token=True)
            assert status == 200, f"Product failed: {prod}"

            status, engines = request_json(f"{endpoint}/api/engines", token=True)
            assert status == 200, f"Engines failed: {engines}"

            # Create sample video & test job creation via engine direct process
            sample_video = root / "sample.mp4"
            create_sample_video(sample_video)
            assert sample_video.is_file()

            from app.engines.video_privacy import VIDEO_PRIVACY_ENGINE

            result = VIDEO_PRIVACY_ENGINE.process(
                sample_video, root / "out", {"mode": "blur"}
            )
            assert len(result.artifacts) == 2, f"Artifacts: {result.artifacts}"
            assert result.artifacts[0].is_file()
            assert result.artifacts[1].is_file()

            print("Video Privacy Studio smoke test SUCCESSFUL!")

        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    main()
