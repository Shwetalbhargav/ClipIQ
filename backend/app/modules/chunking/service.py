"""
Transcript chunking service.

Chunking strategy
-----------------
This service uses a segment-preserving sliding window:

1. Normalize transcript segments.
   - Sort by timestamp and segment index.
   - Remove empty text.
   - Validate timestamp order.

2. Tokenize each segment into lightweight token-like words.
   - We avoid a hard dependency on a tokenizer so this service stays fast and
     easy to test.
   - In production, the tokenizer can be swapped by replacing `_tokenize`.
   - For embedding models, this word-based budget is a practical approximation.
     The default 500-word chunk is intentionally conservative for modern
     embedding context windows.

3. Build chunks with:
   - Maximum 500 token-like words by default.
   - 100 token-like word overlap by default.
   - Timestamp range from the first token's source segment to the last token's
     source segment.
   - Source segment indices for traceability.
   - Deterministic chunk IDs for idempotent indexing.

4. Prefer semantic boundaries when possible.
   - We try to end a chunk at sentence punctuation near the chunk boundary.
   - This keeps chunks readable and usually improves retrieval quality.
   - If no good sentence boundary exists, we fall back to the strict size limit.

Why overlap matters
-------------------
Transcript ideas often span caption boundaries. A 100-token overlap lets adjacent
chunks share trailing context, which improves retrieval for questions like
"compare the hook" or "why did this section perform better" without forcing
huge chunks into the vector DB.

Why timestamps are preserved
----------------------------
Every token keeps a reference to its source segment. The chunk timestamp range is
computed from those source segments, so downstream citations can point users back
to the relevant moment in Video A or Video B.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from .schema import (
    ChunkingRequest,
    ChunkingResult,
    ChunkMetadata,
    TranscriptChunk,
    TranscriptSegment,
)


_SENTENCE_END_RE = re.compile(r"[.!?。！？]$")
_TOKEN_RE = re.compile(r"\S+")


@dataclass(frozen=True)
class _TokenRef:
    """
    Internal token representation.

    A chunk may span many transcript segments. Keeping segment metadata on every
    token lets us compute reliable chunk timestamps and citation metadata even
    when chunks split inside a long segment.
    """

    text: str
    segment_index: int
    start_seconds: float
    end_seconds: float


class TranscriptChunkingService:
    """
    Creates embedding-ready transcript chunks.

    This class is intentionally stateless. It can be safely reused across
    FastAPI requests, background workers, tests, and batch indexing jobs.
    """

    def chunk_transcript(self, request: ChunkingRequest) -> ChunkingResult:
        """
        Convert normalized transcript segments into embedding-ready chunks.

        Args:
            request: ChunkingRequest containing transcript segments and source
                metadata.

        Returns:
            ChunkingResult with validated TranscriptChunk objects.

        Raises:
            ValueError: If there are no usable transcript tokens after cleanup.
        """

        segments = self._normalize_segments(request.segments)
        token_refs = self._segments_to_token_refs(segments)

        if not token_refs:
            raise ValueError("No usable transcript tokens found for chunking.")

        chunks: list[TranscriptChunk] = []
        start = 0
        chunk_index = 0
        step = request.chunk_size - request.overlap

        while start < len(token_refs):
            hard_end = min(start + request.chunk_size, len(token_refs))
            end = self._choose_semantic_end(
                token_refs=token_refs,
                start=start,
                hard_end=hard_end,
                chunk_size=request.chunk_size,
            )

            window = token_refs[start:end]
            if not window:
                break

            chunk_text = self._join_tokens(window)
            metadata = self._build_metadata(
                request=request,
                chunk_index=chunk_index,
                window=window,
                text=chunk_text,
            )

            chunks.append(
                TranscriptChunk(
                    text=chunk_text,
                    metadata=metadata,
                )
            )

            if end >= len(token_refs):
                break

            # Sliding window overlap:
            # Move forward by chunk_size - overlap. This ensures the next chunk
            # repeats the tail of the current chunk, preserving context across
            # boundaries without duplicating the entire chunk.
            next_start = max(end - request.overlap, start + step)

            # Safety guard against infinite loops if configuration changes or
            # semantic boundary selection creates an unexpected boundary.
            if next_start <= start:
                next_start = start + step

            start = next_start
            chunk_index += 1

        return ChunkingResult(
            video_id=request.video_id,
            comparison_id=request.comparison_id,
            total_segments=len(segments),
            total_chunks=len(chunks),
            chunk_size=request.chunk_size,
            overlap=request.overlap,
            chunks=chunks,
        )

    def _normalize_segments(
        self,
        segments: Iterable[TranscriptSegment],
    ) -> list[TranscriptSegment]:
        """
        Sort and clean transcript segments.

        Extractors may return captions slightly out of order or with blank text.
        We normalize here so downstream chunking is deterministic.
        """

        cleaned: list[TranscriptSegment] = []

        for segment in segments:
            text = " ".join(segment.text.split())
            if not text:
                continue

            cleaned.append(
                TranscriptSegment(
                    segment_index=segment.segment_index,
                    text=text,
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    source_type=segment.source_type,
                )
            )

        return sorted(
            cleaned,
            key=lambda item: (item.start_seconds, item.segment_index),
        )

    def _segments_to_token_refs(
        self,
        segments: Iterable[TranscriptSegment],
    ) -> list[_TokenRef]:
        """
        Convert transcript segments into token refs.

        Timestamp precision:
        - Captions usually expose timestamps at segment level, not word level.
        - We assign every token in the segment the same segment timestamp.
        - This is still citation-safe because the citation points to the segment
          range that contains the text.
        """

        token_refs: list[_TokenRef] = []

        for segment in segments:
            for token in self._tokenize(segment.text):
                token_refs.append(
                    _TokenRef(
                        text=token,
                        segment_index=segment.segment_index,
                        start_seconds=segment.start_seconds,
                        end_seconds=segment.end_seconds,
                    )
                )

        return token_refs

    def _tokenize(self, text: str) -> list[str]:
        """
        Lightweight tokenizer.

        We deliberately use regex tokenization instead of adding a dependency on
        tiktoken or a provider-specific tokenizer. That keeps this module stable
        and portable. If exact model token counting becomes necessary, replace
        this method with a tokenizer adapter and keep the public API unchanged.
        """

        return _TOKEN_RE.findall(text)

    def _choose_semantic_end(
        self,
        token_refs: list[_TokenRef],
        start: int,
        hard_end: int,
        chunk_size: int,
    ) -> int:
        """
        Pick a readable chunk boundary near the hard size limit.

        We search backward from the hard boundary for a sentence-ending token.
        To avoid tiny chunks, we only accept sentence boundaries after 70% of the
        requested chunk size. If none exists, we use the hard boundary.
        """

        if hard_end >= len(token_refs):
            return hard_end

        minimum_acceptable_end = start + int(chunk_size * 0.70)

        for index in range(hard_end - 1, minimum_acceptable_end - 1, -1):
            if _SENTENCE_END_RE.search(token_refs[index].text):
                return index + 1

        return hard_end

    def _join_tokens(self, token_refs: list[_TokenRef]) -> str:
        """
        Join tokens into chunk text.

        This keeps text compact for embedding while preserving the transcript
        content exactly enough for retrieval and source citations.
        """

        return " ".join(token.text for token in token_refs).strip()

    def _build_metadata(
        self,
        request: ChunkingRequest,
        chunk_index: int,
        window: list[_TokenRef],
        text: str,
    ) -> ChunkMetadata:
        """
        Build vector-store-ready metadata for a chunk.

        `chunk_id` is deterministic. Re-running chunking on the same video with
        the same transcript and strategy produces the same chunk IDs, which makes
        indexing idempotent and prevents duplicate vector points.
        """

        segment_indices = [token.segment_index for token in window]
        segment_start_index = min(segment_indices)
        segment_end_index = max(segment_indices)

        start_seconds = min(token.start_seconds for token in window)
        end_seconds = max(token.end_seconds for token in window)

        chunk_id = self._make_chunk_id(
            comparison_id=request.comparison_id,
            video_id=request.video_id,
            chunk_index=chunk_index,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            text=text,
        )

        return ChunkMetadata(
            comparison_id=request.comparison_id,
            video_id=request.video_id,
            platform=request.platform,
            source_url=request.source_url,
            creator=request.creator,
            chunk_index=chunk_index,
            chunk_id=chunk_id,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            token_count=len(window),
            char_count=len(text),
            segment_start_index=segment_start_index,
            segment_end_index=segment_end_index,
            source_segment_indices=sorted(set(segment_indices)),
            chunk_size=request.chunk_size,
            overlap=request.overlap,
            extra=request.metadata_extra,
        )

    def _make_chunk_id(
        self,
        comparison_id: str | None,
        video_id: str,
        chunk_index: int,
        start_seconds: float,
        end_seconds: float,
        text: str,
    ) -> str:
        """
        Create a stable chunk ID.

        The hash includes a small text fingerprint so the ID changes when the
        transcript content changes, while still remaining deterministic across
        retries for the same input.
        """

        raw = "|".join(
            [
                comparison_id or "no-comparison",
                video_id,
                str(chunk_index),
                f"{start_seconds:.3f}",
                f"{end_seconds:.3f}",
                text[:500],
            ]
        )

        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{video_id}:chunk:{chunk_index}:{digest}"