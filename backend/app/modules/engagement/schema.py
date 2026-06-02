"""Schemas for ClipIQ engagement analysis.

The engagement module intentionally contains no database, HTTP, or LLM code. It can be
used from extraction workers, FastAPI handlers, LangGraph context builders, or tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

VideoLabel = Literal["A", "B"]
EngagementStatus = Literal["available", "unavailable"]
ComparisonOutcome = Literal["A", "B", "tie", "unavailable"]

ENGAGEMENT_FORMULA_VERSION = "likes_comments_over_views_v1"
ENGAGEMENT_FORMULA = "((likes + comments) / views) * 100"


@dataclass(frozen=True, slots=True)
class VideoEngagementInput:
    """Normalized metrics needed to calculate engagement for one video.

    `views` should be YouTube views, Instagram plays, or Instagram view_count,
    depending on which normalized field the extractor could provide.

    A metric set to `None` means unavailable. That is different from `0`, which
    means the platform returned a real zero. This distinction matters because the
    product requirements explicitly say not to fabricate missing metrics.
    """

    video_id: str
    label: VideoLabel
    platform: str
    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    creator: Optional[str] = None
    title: Optional[str] = None
    follower_count: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngagementMetric:
    """Calculated engagement payload for one video."""

    video_id: str
    label: VideoLabel
    platform: str
    views: Optional[int]
    likes: Optional[int]
    comments: Optional[int]
    engagement_rate: Optional[float]
    engagement_rate_percent: Optional[float]
    formula: str
    formula_version: str
    status: EngagementStatus
    unavailable_reason: Optional[str] = None
    creator: Optional[str] = None
    title: Optional[str] = None
    follower_count: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None


@dataclass(frozen=True, slots=True)
class EngagementDelta:
    """A/B comparison deltas for engagement metrics.

    Absolute delta is expressed in percentage points because engagement_rate is
    already a percent value. Relative lift is expressed as a percent improvement
    over the lower/baseline video when both rates are available.
    """

    winner: ComparisonOutcome
    loser: ComparisonOutcome
    absolute_delta_points: Optional[float]
    relative_lift_percent: Optional[float]
    explanation: str


@dataclass(frozen=True, slots=True)
class EngagementComparison:
    """Full Video A vs Video B engagement analysis."""

    video_a: EngagementMetric
    video_b: EngagementMetric
    delta: EngagementDelta
    summary: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly structure without requiring a framework model."""

        return {
            "video_a": asdict(self.video_a),
            "video_b": asdict(self.video_b),
            "delta": asdict(self.delta),
            "summary": self.summary,
        }
