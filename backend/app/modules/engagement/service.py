"""Engagement metric calculation and A/B comparison service.

Formula used by ClipIQ MVP:
    engagement_rate = ((likes + comments) / views) * 100

The functions are pure and dependency-free so they are easy to test and safe to
reuse from API handlers, workers, and LangGraph context-building nodes.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from .schema import (
    ENGAGEMENT_FORMULA,
    ENGAGEMENT_FORMULA_VERSION,
    EngagementComparison,
    EngagementDelta,
    EngagementMetric,
    VideoEngagementInput,
)

DEFAULT_DECIMAL_PLACES = 2


def _round_percent(value: Decimal, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> float:
    """Round percentages with business-friendly half-up behavior.

    Python's built-in round uses bankers' rounding, which can surprise users in
    analytics UI. Decimal + ROUND_HALF_UP gives predictable display values.
    """

    quantizer = Decimal("1") if decimal_places == 0 else Decimal(f"1e-{decimal_places}")
    return float(value.quantize(quantizer, rounding=ROUND_HALF_UP))


def _missing_metric_reason(video: VideoEngagementInput) -> Optional[str]:
    """Return why the MVP engagement rate cannot be calculated, if applicable."""

    missing_fields = [
        field_name
        for field_name in ("views", "likes", "comments")
        if getattr(video, field_name) is None
    ]
    if missing_fields:
        return f"missing required metric(s): {', '.join(missing_fields)}"
    if video.views == 0:
        return "views denominator is zero"
    if video.views is not None and video.views < 0:
        return "views cannot be negative"
    if video.likes is not None and video.likes < 0:
        return "likes cannot be negative"
    if video.comments is not None and video.comments < 0:
        return "comments cannot be negative"
    return None


def calculate_engagement(video: VideoEngagementInput, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> EngagementMetric:
    """Calculate engagement metrics for one video.

    MVP formula:
        engagement_rate = ((likes + comments) / views) * 100

    `None` is returned for the rate when views/likes/comments are unavailable or
    when views is zero. This preserves the important product distinction between
    unavailable platform data and a real metric value of 0.
    """

    unavailable_reason = _missing_metric_reason(video)
    if unavailable_reason:
        return EngagementMetric(
            video_id=video.video_id,
            label=video.label,
            platform=video.platform,
            views=video.views,
            likes=video.likes,
            comments=video.comments,
            engagement_rate=None,
            engagement_rate_percent=None,
            formula=ENGAGEMENT_FORMULA,
            formula_version=ENGAGEMENT_FORMULA_VERSION,
            status="unavailable",
            unavailable_reason=unavailable_reason,
            creator=video.creator,
            title=video.title,
            follower_count=video.follower_count,
            shares=video.shares,
            saves=video.saves,
        )

    # likes/comments/views are known non-negative ints here. Decimal prevents
    # floating-point drift in a value that gets persisted and shown in analytics.
    raw_rate = (Decimal(video.likes + video.comments) / Decimal(video.views)) * Decimal(100)
    rounded_rate = _round_percent(raw_rate, decimal_places)

    return EngagementMetric(
        video_id=video.video_id,
        label=video.label,
        platform=video.platform,
        views=video.views,
        likes=video.likes,
        comments=video.comments,
        engagement_rate=rounded_rate,
        engagement_rate_percent=rounded_rate,
        formula=ENGAGEMENT_FORMULA,
        formula_version=ENGAGEMENT_FORMULA_VERSION,
        status="available",
        unavailable_reason=None,
        creator=video.creator,
        title=video.title,
        follower_count=video.follower_count,
        shares=video.shares,
        saves=video.saves,
    )


def compare_videos(
    video_a: VideoEngagementInput,
    video_b: VideoEngagementInput,
    decimal_places: int = DEFAULT_DECIMAL_PLACES,
) -> EngagementComparison:
    """Compare Video A vs Video B and return an analytics-ready summary."""

    metric_a = calculate_engagement(video_a, decimal_places=decimal_places)
    metric_b = calculate_engagement(video_b, decimal_places=decimal_places)
    delta = calculate_delta(metric_a, metric_b, decimal_places=decimal_places)
    summary = build_analytics_summary(metric_a, metric_b, delta)
    return EngagementComparison(video_a=metric_a, video_b=metric_b, delta=delta, summary=summary)


def calculate_delta(
    metric_a: EngagementMetric,
    metric_b: EngagementMetric,
    decimal_places: int = DEFAULT_DECIMAL_PLACES,
) -> EngagementDelta:
    """Calculate winner, absolute percentage-point delta, and relative lift."""

    if metric_a.engagement_rate is None or metric_b.engagement_rate is None:
        return EngagementDelta(
            winner="unavailable",
            loser="unavailable",
            absolute_delta_points=None,
            relative_lift_percent=None,
            explanation="Comparison unavailable because at least one video is missing engagement rate data.",
        )

    rate_a = Decimal(str(metric_a.engagement_rate))
    rate_b = Decimal(str(metric_b.engagement_rate))

    if rate_a == rate_b:
        return EngagementDelta(
            winner="tie",
            loser="tie",
            absolute_delta_points=0.0,
            relative_lift_percent=0.0,
            explanation=f"Both videos have the same engagement rate: {metric_a.engagement_rate}%.",
        )

    winner = "A" if rate_a > rate_b else "B"
    loser = "B" if winner == "A" else "A"
    higher = max(rate_a, rate_b)
    lower = min(rate_a, rate_b)
    absolute_delta = higher - lower

    # Relative lift answers: "how much higher was the winner vs the loser?" If
    # the loser has a 0% rate, relative lift is undefined rather than infinite.
    relative_lift = None if lower == 0 else ((higher - lower) / lower) * Decimal(100)

    rounded_absolute = _round_percent(absolute_delta, decimal_places)
    rounded_relative = None if relative_lift is None else _round_percent(relative_lift, decimal_places)

    lift_phrase = (
        "relative lift is undefined because the lower engagement rate is 0%"
        if rounded_relative is None
        else f"a {rounded_relative}% relative lift"
    )
    return EngagementDelta(
        winner=winner,
        loser=loser,
        absolute_delta_points=rounded_absolute,
        relative_lift_percent=rounded_relative,
        explanation=(
            f"Video {winner} leads Video {loser} by {rounded_absolute} percentage points, "
            f"which is {lift_phrase}."
        ),
    )


def build_analytics_summary(
    metric_a: EngagementMetric,
    metric_b: EngagementMetric,
    delta: EngagementDelta,
) -> str:
    """Create a compact summary suitable for API responses or prompt context."""

    a_rate = _format_rate(metric_a)
    b_rate = _format_rate(metric_b)

    if delta.winner == "unavailable":
        return (
            f"Video A engagement is {a_rate}; Video B engagement is {b_rate}. "
            "A/B comparison is unavailable until both videos have views, likes, and comments."
        )

    if delta.winner == "tie":
        return f"Video A and Video B are tied at {a_rate} engagement."

    return (
        f"Video A engagement is {a_rate}; Video B engagement is {b_rate}. "
        f"{delta.explanation}"
    )


def summarize_collection(videos: Iterable[VideoEngagementInput]) -> list[EngagementMetric]:
    """Calculate engagement for any iterable of videos.

    Handy for tests, batch worker code, or future multi-video comparisons without
    tying the module to the A/B-only API surface.
    """

    return [calculate_engagement(video) for video in videos]


def _format_rate(metric: EngagementMetric) -> str:
    """Display available rates as percents and missing values as unavailable."""

    if metric.engagement_rate is None:
        return f"unavailable ({metric.unavailable_reason})"
    return f"{metric.engagement_rate}%"
