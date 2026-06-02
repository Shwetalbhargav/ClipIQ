"""Citation helpers for retrieved transcript chunks."""

from __future__ import annotations

import re
from hashlib import sha1

from .schema import Citation, RetrievedChunk, SourceKind

_MAX_QUOTE_CHARS = 240
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_excerpt(text: str, max_chars: int = _MAX_QUOTE_CHARS) -> str:
    """Return a compact excerpt suitable for prompts, UI, and persistence."""

    cleaned = _WHITESPACE_RE.sub(" ", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 1].rstrip()}…"


def format_timestamp(seconds: float | None) -> str | None:
    """Format seconds as mm:ss for creator-friendly citation labels."""

    if seconds is None:
        return None
    total_seconds = max(0, int(seconds))
    minutes, remaining_seconds = divmod(total_seconds, 60)
    return f"{minutes}:{remaining_seconds:02d}"


def build_citation_label(chunk: RetrievedChunk) -> str:
    """Create a readable citation label, e.g. `Video A · Chunk 3 · 0:05-0:12`."""

    metadata = chunk.metadata
    video = f"Video {metadata.video_label}" if metadata.video_label else metadata.video_id
    parts = [video, f"Chunk {metadata.chunk_index}"]

    start = format_timestamp(metadata.start_seconds)
    end = format_timestamp(metadata.end_seconds)
    if start and end:
        parts.append(f"{start}-{end}")
    elif start:
        parts.append(start)

    return " · ".join(parts)


def build_citation_id(chunk: RetrievedChunk) -> str:
    """Create a deterministic citation id so repeat retrievals are traceable."""

    metadata = chunk.metadata
    raw = f"{metadata.comparison_id}:{metadata.video_id}:{metadata.chunk_id}:{metadata.chunk_index}"
    return sha1(raw.encode("utf-8")).hexdigest()[:12]


def citation_from_chunk(chunk: RetrievedChunk) -> Citation:
    """Convert a retrieved chunk into the citation object used by chat responses."""

    metadata = chunk.metadata
    return Citation(
        citation_id=build_citation_id(chunk),
        label=build_citation_label(chunk),
        source_kind=SourceKind.TRANSCRIPT_CHUNK,
        video_id=metadata.video_id,
        video_label=metadata.video_label,
        platform=metadata.platform,
        chunk_id=metadata.chunk_id,
        chunk_index=metadata.chunk_index,
        start_seconds=metadata.start_seconds,
        end_seconds=metadata.end_seconds,
        quoted_text=normalize_excerpt(chunk.text),
        score=chunk.score,
        source_url=metadata.source_url,
    )


def generate_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Generate one citation per retrieved chunk, preserving ranked order."""

    return [citation_from_chunk(chunk) for chunk in chunks]
