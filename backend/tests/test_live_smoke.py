"""Optional live demo smoke test.

Run only when a real backend and real public video URLs are available:

    $env:CLIPIQ_LIVE_SMOKE="1"
    $env:CLIPIQ_API_BASE="http://localhost:8000"
    $env:CLIPIQ_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
    $env:CLIPIQ_INSTAGRAM_REEL_URL="https://www.instagram.com/reel/.../"
    python -m pytest tests/test_live_smoke.py -q
"""

from __future__ import annotations

import os

import httpx
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("CLIPIQ_LIVE_SMOKE") != "1",
    reason="set CLIPIQ_LIVE_SMOKE=1 with real URLs to run live extractor smoke test",
)


def test_live_comparison_endpoint_with_real_urls() -> None:
    api_base = os.getenv("CLIPIQ_API_BASE", "http://localhost:8000").rstrip("/")
    youtube_url = os.environ["CLIPIQ_YOUTUBE_URL"]
    instagram_url = os.environ["CLIPIQ_INSTAGRAM_REEL_URL"]

    response = httpx.post(
        f"{api_base}/api/comparisons",
        json={"youtube_url": youtube_url, "instagram_url": instagram_url},
        timeout=180,
    )
    assert response.status_code in {200, 201}, response.text
    body = response.json()
    assert body["comparison_id"]
    assert body["video_a"]["platform"] == "youtube"
    assert body["video_b"]["platform"] == "instagram"
    assert body["video_a"]["video_id"]
    assert body["video_b"]["video_id"]
    assert body["status"] in {"ready", "partial"}
