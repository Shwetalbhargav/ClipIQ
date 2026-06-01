"""Utility helpers for ClipIQ video ingestion.

The helpers in this file are intentionally pure and side-effect free. They are
safe to unit test without network access and keep platform parsing rules out of
router/service code.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

from .schema import SupportedPlatform

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}

_HASHTAG_RE = re.compile(r"(?<!\w)#([\w]+)", flags=re.UNICODE)
_INSTAGRAM_REEL_RE = re.compile(r"^/(?:reel|reels|p)/(?P<shortcode>[A-Za-z0-9_-]+)/?")
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,}$")


class UnsupportedVideoUrlError(ValueError):
    """Raised when a URL does not belong to a supported ClipIQ platform."""


class InvalidVideoUrlError(ValueError):
    """Raised when a supported platform URL is malformed or incomplete."""


def detect_platform(url: str) -> SupportedPlatform:
    """Return the supported platform represented by ``url``.

    Args:
        url: Raw user-provided URL.

    Raises:
        UnsupportedVideoUrlError: If the host is not YouTube or Instagram.
    """

    host = urlparse(url).netloc.lower()
    if host in YOUTUBE_HOSTS:
        return SupportedPlatform.YOUTUBE
    if host in INSTAGRAM_HOSTS:
        return SupportedPlatform.INSTAGRAM
    raise UnsupportedVideoUrlError("Only YouTube video and Instagram Reel URLs are supported.")


def extract_youtube_video_id(url: str) -> str:
    """Extract a YouTube video ID from standard, short, embed, or shorts URLs."""

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        video_id = path_parts[0]
    elif path_parts and path_parts[0] in {"embed", "shorts", "live"} and len(path_parts) > 1:
        video_id = path_parts[1]
    else:
        query = parse_qs(parsed.query)
        video_id = query.get("v", [""])[0]

    if not video_id or not _YOUTUBE_ID_RE.match(video_id):
        raise InvalidVideoUrlError("Could not extract a valid YouTube video ID from the URL.")
    return video_id


def extract_instagram_shortcode(url: str) -> str:
    """Extract an Instagram Reel/Post shortcode from an Instagram URL."""

    parsed = urlparse(url)
    match = _INSTAGRAM_REEL_RE.match(parsed.path)
    if not match:
        raise InvalidVideoUrlError("Instagram URLs must point to a Reel or post shortcode.")
    return match.group("shortcode")


def canonicalize_url(url: str) -> str:
    """Convert supported video URLs into stable canonical URLs.

    Canonical URLs are used for cache keys and deduplication. Query strings are
    intentionally discarded because tracking params should not produce separate
    video records.
    """

    platform = detect_platform(url)
    if platform == SupportedPlatform.YOUTUBE:
        video_id = extract_youtube_video_id(url)
        return f"https://www.youtube.com/watch?v={video_id}"

    shortcode = extract_instagram_shortcode(url)
    return f"https://www.instagram.com/reel/{shortcode}/"


def strip_query_and_fragment(url: str) -> str:
    """Return a URL without query string or fragment components."""

    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def extract_platform_video_id(url: str) -> str:
    """Extract the platform-native video identifier from a supported URL."""

    platform = detect_platform(url)
    if platform == SupportedPlatform.YOUTUBE:
        return extract_youtube_video_id(url)
    return extract_instagram_shortcode(url)


def extract_hashtags(*texts: str | None) -> list[str]:
    """Extract unique hashtags from one or more metadata text fields.

    Tags are returned without the leading ``#`` and normalized to lowercase so
    downstream comparison logic can treat ``#AI`` and ``#ai`` as the same tag.
    """

    seen: set[str] = set()
    hashtags: list[str] = []
    for text in texts:
        if not text:
            continue
        for match in _HASHTAG_RE.finditer(text):
            tag = match.group(1).lower()
            if tag not in seen:
                hashtags.append(tag)
                seen.add(tag)
    return hashtags


def parse_upload_date(value: Any) -> datetime | None:
    """Parse common extractor date formats into timezone-aware datetimes."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if re.fullmatch(r"\d{8}", cleaned):
            return datetime.strptime(cleaned, "%Y%m%d").replace(tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def coerce_int(value: Any) -> int | None:
    """Best-effort conversion of extractor metric values into non-negative ints."""

    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        converted = int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None
    return converted if converted >= 0 else None


def coerce_float(value: Any) -> float | None:
    """Best-effort conversion of extractor duration values into floats."""

    if value is None or value == "":
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if converted >= 0 else None
