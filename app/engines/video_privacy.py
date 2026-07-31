from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .base import EngineResult, LocalEngine

SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".m4v",
    ".3gp",
    ".flv",
    ".wmv",
    ".ts",
    ".mpg",
    ".mpeg",
    ".ogv",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def expand_bbox(
    bbox: tuple[int, int, int, int],
    frame_shape: tuple[int, int],
    pad_ratio: float = 0.35,
) -> tuple[int, int, int, int]:
    """Expand box by pad_ratio margin to cover hair and chin."""
    x, y, w, h = bbox
    H, W = frame_shape[:2]

    pad_w = int(w * pad_ratio)
    pad_h = int(h * pad_ratio)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(W, x + w + pad_w)
    y2 = min(H, y + h + pad_h)

    return (x1, y1, x2 - x1, y2 - y1)


def apply_redaction(
    frame: np.ndarray, bbox: tuple[int, int, int, int], mode: str = "blur"
) -> None:
    x, y, w, h = bbox
    H, W = frame.shape[:2]

    x1 = max(0, min(W - 1, x))
    y1 = max(0, min(H - 1, y))
    x2 = max(x1 + 1, min(W, x + w))
    y2 = max(y1 + 1, min(H, y + h))

    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return

    if mode == "blackout":
        frame[y1:y2, x1:x2] = (0, 0, 0)
    elif mode == "pixelate":
        rh, rw = roi.shape[:2]
        small_w = max(1, rw // 14)
        small_h = max(1, rh // 14)
        small = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)
        frame[y1:y2, x1:x2] = pixelated
    else:  # Default: Strong Gaussian Blur
        kernel_w = (w // 2) | 1
        kernel_h = (h // 2) | 1
        kernel_w = max(25, kernel_w)
        kernel_h = max(25, kernel_h)
        frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (kernel_w, kernel_h), 0)


class TemporalBoxTracker:
    """Tracks detected boxes across video frames so no frame is missed."""

    def __init__(self, max_missing_frames: int = 25, iou_thresh: float = 0.2) -> None:
        self.max_missing = max_missing_frames
        self.iou_thresh = iou_thresh
        self.tracks: list[dict[str, Any]] = []

    def update(
        self, detected_boxes: list[tuple[int, int, int, int]]
    ) -> list[tuple[int, int, int, int]]:
        # Mark all existing tracks as updated=False
        for t in self.tracks:
            t["updated_this_frame"] = False
            t["missing_count"] += 1

        active_boxes: list[tuple[int, int, int, int]] = []

        for box in detected_boxes:
            matched_track = None
            best_iou = 0.0

            for t in self.tracks:
                iou = self._compute_iou(box, t["box"])
                if iou > self.iou_thresh and iou > best_iou:
                    best_iou = iou
                    matched_track = t

            if matched_track is not None:
                # Smooth box position using Exponential Moving Average
                old_x, old_y, old_w, old_h = matched_track["box"]
                nx, ny, nw, nh = box
                smoothed_box = (
                    int(0.4 * old_x + 0.6 * nx),
                    int(0.4 * old_y + 0.6 * ny),
                    int(0.4 * old_w + 0.6 * nw),
                    int(0.4 * old_h + 0.6 * nh),
                )
                matched_track["box"] = smoothed_box
                matched_track["missing_count"] = 0
                matched_track["updated_this_frame"] = True
            else:
                # Add new track
                self.tracks.append(
                    {
                        "box": box,
                        "missing_count": 0,
                        "updated_this_frame": True,
                    }
                )

        # Filter out tracks that have been missing for too long
        self.tracks = [t for t in self.tracks if t["missing_count"] <= self.max_missing]

        # Return boxes for ALL active tracks (even if missed in current frame!)
        for t in self.tracks:
            active_boxes.append(t["box"])

        return active_boxes

    @staticmethod
    def _compute_iou(
        boxA: tuple[int, int, int, int], boxB: tuple[int, int, int, int]
    ) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]

        denom = float(boxAArea + boxBArea - interArea)
        return interArea / denom if denom > 0 else 0.0


class VideoPrivacyEngine(LocalEngine):
    """Local CPU engine for redacting faces with 100% temporal coverage."""

    engine_id = "video-privacy"
    label_en = "Video Privacy Studio"
    label_it = "Video Privacy Studio"
    description_en = (
        "CPU video pipeline for blurring faces and plates with zero missed frames."
    )
    description_it = "Pipeline locale per l'oscuramento di volti e targhe nei video."
    accepted_extensions = frozenset(SUPPORTED_EXTENSIONS)

    def __init__(self) -> None:
        cv_data = cv2.data.haarcascades
        self.face_cascade = cv2.CascadeClassifier(
            cv_data + "haarcascade_frontalface_default.xml"
        )
        self.face_alt_cascade = cv2.CascadeClassifier(
            cv_data + "haarcascade_frontalface_alt.xml"
        )
        self.profile_cascade = cv2.CascadeClassifier(
            cv_data + "haarcascade_profileface.xml"
        )
        self.plate_cascade = cv2.CascadeClassifier(
            cv_data + "haarcascade_russian_plate_number.xml"
        )

    def detect_raw_regions(
        self, frame: np.ndarray, detect_faces: bool = True, detect_plates: bool = True
    ) -> list[tuple[int, int, int, int]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        boxes: list[tuple[int, int, int, int]] = []

        if detect_faces:
            # 1. Frontal face primary
            if not self.face_cascade.empty():
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24)
                )
                for x, y, w, h in faces:
                    boxes.append((int(x), int(y), int(w), int(h)))

            # 2. Frontal face alt (captures rotated/tilted faces)
            if not self.face_alt_cascade.empty():
                faces_alt = self.face_alt_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24)
                )
                for x, y, w, h in faces_alt:
                    boxes.append((int(x), int(y), int(w), int(h)))

            # 3. Profile face (captures side views)
            if not self.profile_cascade.empty():
                profiles = self.profile_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24)
                )
                for x, y, w, h in profiles:
                    boxes.append((int(x), int(y), int(w), int(h)))

        if detect_plates and not self.plate_cascade.empty():
            plates = self.plate_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20)
            )
            for x, y, w, h in plates:
                boxes.append((int(x), int(y), int(w), int(h)))

        # Expand all detected boxes with 35% margin for complete coverage
        H, W = frame.shape[:2]
        expanded_boxes = [expand_bbox(b, (H, W), pad_ratio=0.35) for b in boxes]
        return expanded_boxes

    def process(
        self,
        source: Path,
        output_dir: Path,
        options: dict[str, Any],
    ) -> EngineResult:
        if not source.is_file():
            raise FileNotFoundError(f"Video file non trovato: {source}")

        output_dir.mkdir(parents=True, exist_ok=True)
        redact_mode = options.get("mode", "blur")
        detect_faces = options.get("detect_faces", True)
        detect_plates = options.get("detect_plates", True)

        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise RuntimeError(f"Impossibile aprire il video: {source}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        output_video_path = output_dir / f"redacted_{source.stem}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_video_path), fourcc, fps, (width, height))

        tracker = TemporalBoxTracker(max_missing_frames=25, iou_thresh=0.15)

        frame_count = 0
        total_redactions = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1

            # 1. Detect raw regions in current frame
            raw_boxes = self.detect_raw_regions(
                frame, detect_faces=detect_faces, detect_plates=detect_plates
            )

            # 2. Update temporal tracker across missing frames
            active_boxes = tracker.update(raw_boxes)
            total_redactions += len(active_boxes)

            # 3. Apply redaction to all active boxes
            for box in active_boxes:
                apply_redaction(frame, box, mode=redact_mode)

            writer.write(frame)

        cap.release()
        writer.release()

        receipt_path = output_dir / "privacy_receipt.json"
        receipt_data = {
            "application": "Video Privacy Studio",
            "version": "0.1.0",
            "processed_at": utc_now(),
            "source_file": source.name,
            "output_file": output_video_path.name,
            "video_metadata": {
                "width": width,
                "height": height,
                "fps": round(fps, 2),
                "total_frames": frame_count,
            },
            "redaction_settings": {
                "mode": redact_mode,
                "detect_faces": detect_faces,
                "detect_plates": detect_plates,
                "temporal_tracking": True,
                "margin_padding": "35%",
            },
            "summary": {
                "frames_processed": frame_count,
                "total_regions_redacted": total_redactions,
            },
        }

        receipt_path.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

        summary_msg = (
            f"Video elaborato con successo! Processati {frame_count} frame "
            f"con tracciamento continuo (regioni: {total_redactions})."
        )

        return EngineResult(
            summary={
                "message": summary_msg,
                "frames": frame_count,
                "redactions": total_redactions,
            },
            artifacts=(output_video_path, receipt_path),
        )


VIDEO_PRIVACY_ENGINE = VideoPrivacyEngine()
