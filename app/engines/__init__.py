from __future__ import annotations

from .video_privacy import VIDEO_PRIVACY_ENGINE, VideoPrivacyEngine

ENGINES = {
    VIDEO_PRIVACY_ENGINE.engine_id: VIDEO_PRIVACY_ENGINE,
}

__all__ = ["ENGINES", "VIDEO_PRIVACY_ENGINE", "VideoPrivacyEngine"]
