from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

_TEST_ROOT = tempfile.TemporaryDirectory(prefix="video-privacy-unit-")
os.environ["VIDEO_PRIVACY_STUDIO_DATA"] = str(Path(_TEST_ROOT.name) / "data")
os.environ["VIDEO_PRIVACY_STUDIO_STATE"] = str(Path(_TEST_ROOT.name) / "state")
os.environ["VIDEO_PRIVACY_STUDIO_OUTPUTS"] = str(Path(_TEST_ROOT.name) / "outputs")

from app.engines.video_privacy import (  # noqa: E402
    VIDEO_PRIVACY_ENGINE,
    apply_redaction,
)
from app.product import load_product  # noqa: E402
from app.security import TOKEN_COOKIE  # noqa: E402
from app.store import JobStore  # noqa: E402
from app.utils import resolve_artifact, safe_name  # noqa: E402
from scripts.start import guarded_environment  # noqa: E402


class ProductTests(unittest.TestCase):
    def test_product_file_is_valid(self) -> None:
        product = load_product()
        self.assertEqual(product.slug, "video-privacy-studio")
        self.assertEqual(product.name, "Video Privacy Studio")
        self.assertIn(product.default_language, {"it", "en"})
        self.assertEqual(TOKEN_COOKIE, "video_privacy_studio_token")

    def test_launcher_removes_inherited_injection_paths(self) -> None:
        hostile = {
            "LD_PRELOAD": "/tmp/not-a-real-library.so",
            "PYTHONHOME": "/tmp/not-a-python-home",
            "PYTHONPATH": "/tmp/not-a-python-path",
        }
        with mock.patch.dict(os.environ, hostile, clear=False):
            environment = guarded_environment("x" * 48, 54321)
        self.assertNotIn("PYTHONHOME", environment)
        self.assertNotEqual(environment.get("LD_PRELOAD"), hostile["LD_PRELOAD"])
        self.assertTrue(environment["PYTHONPATH"].endswith("runtime_guard"))
        self.assertEqual(environment["LOCAL_AI_APP_PORT"], "54321")


class PathTests(unittest.TestCase):
    def test_upload_name_is_reduced_to_a_safe_basename(self) -> None:
        self.assertEqual(safe_name("../../private video.mp4"), "private video.mp4")
        self.assertEqual(safe_name(r"..\..\private.mov"), "private.mov")
        self.assertEqual(safe_name(".."), "document")

    def test_artifact_path_cannot_escape_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ok.txt").write_text("ok", encoding="utf-8")
            self.assertEqual(
                resolve_artifact(root, "ok.txt"), (root / "ok.txt").resolve()
            )
            with self.assertRaises(ValueError):
                resolve_artifact(root, "../secret.txt")


class VideoPrivacyEngineTests(unittest.TestCase):
    def test_accepts_extensions(self) -> None:
        self.assertTrue(VIDEO_PRIVACY_ENGINE.accepts(Path("video.mp4")))
        self.assertTrue(VIDEO_PRIVACY_ENGINE.accepts(Path("clip.mov")))
        self.assertFalse(VIDEO_PRIVACY_ENGINE.accepts(Path("photo.jpg")))

    def test_apply_redaction_modes(self) -> None:
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
        bbox = (10, 10, 40, 40)

        # Blackout
        apply_redaction(frame, bbox, mode="blackout")
        self.assertEqual(int(frame[20, 20, 0]), 0)

        # Pixelate
        frame_pix = np.ones((100, 100, 3), dtype=np.uint8) * 255
        apply_redaction(frame_pix, bbox, mode="pixelate")

        # Blur
        frame_blur = np.ones((100, 100, 3), dtype=np.uint8) * 255
        apply_redaction(frame_blur, bbox, mode="blur")


class JobStoreTests(unittest.TestCase):
    def test_create_get_list_clear_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            db_path = Path(temporary) / "test_store.sqlite3"
            store = JobStore(database=db_path)

            job = store.create(
                job_id="test-job-123",
                engine="video-privacy",
                input_name="sample.mp4",
                options={"mode": "blur"},
            )
            self.assertEqual(job["status"], "uploading")

            fetched = store.get("test-job-123")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["input_name"], "sample.mp4")

            jobs = store.list()
            self.assertEqual(len(jobs), 1)

            cleared = store.clear_all()
            self.assertEqual(cleared, 1)
            self.assertEqual(len(store.list()), 0)
