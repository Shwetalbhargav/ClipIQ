import pytest

from app.modules.engagement import (
    ENGAGEMENT_FORMULA,
    ENGAGEMENT_FORMULA_VERSION,
    VideoEngagementInput,
    calculate_engagement,
    compare_videos,
    summarize_collection,
)


def make_video(label="A", views=1000, likes=80, comments=20, video_id=None):
    return VideoEngagementInput(
        video_id=video_id or f"video-{label.lower()}",
        label=label,
        platform="youtube" if label == "A" else "instagram",
        views=views,
        likes=likes,
        comments=comments,
        creator=f"creator-{label.lower()}",
        title=f"Video {label}",
    )


def test_calculate_engagement_uses_mvp_formula():
    metric = calculate_engagement(make_video(views=1000, likes=80, comments=20))

    assert metric.status == "available"
    assert metric.engagement_rate == 10.0
    assert metric.engagement_rate_percent == 10.0
    assert metric.formula == ENGAGEMENT_FORMULA
    assert metric.formula_version == ENGAGEMENT_FORMULA_VERSION


@pytest.mark.parametrize(
    "views, likes, comments, reason",
    [
        (None, 10, 1, "views"),
        (100, None, 1, "likes"),
        (100, 10, None, "comments"),
        (0, 10, 1, "denominator is zero"),
    ],
)
def test_calculate_engagement_returns_unavailable_for_missing_or_zero_denominator(
    views, likes, comments, reason
):
    metric = calculate_engagement(make_video(views=views, likes=likes, comments=comments))

    assert metric.status == "unavailable"
    assert metric.engagement_rate is None
    assert reason in metric.unavailable_reason


@pytest.mark.parametrize(
    "field_name",
    ["views", "likes", "comments"],
)
def test_calculate_engagement_rejects_negative_metrics(field_name):
    kwargs = {"views": 100, "likes": 10, "comments": 1}
    kwargs[field_name] = -1

    metric = calculate_engagement(make_video(**kwargs))

    assert metric.status == "unavailable"
    assert "cannot be negative" in metric.unavailable_reason


def test_compare_videos_identifies_winner_and_delta():
    video_a = make_video(label="A", views=1000, likes=90, comments=10)  # 10%
    video_b = make_video(label="B", views=2000, likes=100, comments=20)  # 6%

    comparison = compare_videos(video_a, video_b)

    assert comparison.video_a.engagement_rate == 10.0
    assert comparison.video_b.engagement_rate == 6.0
    assert comparison.delta.winner == "A"
    assert comparison.delta.loser == "B"
    assert comparison.delta.absolute_delta_points == 4.0
    assert comparison.delta.relative_lift_percent == 66.67
    assert "Video A leads Video B" in comparison.summary


def test_compare_videos_handles_tie():
    video_a = make_video(label="A", views=1000, likes=90, comments=10)
    video_b = make_video(label="B", views=500, likes=45, comments=5)

    comparison = compare_videos(video_a, video_b)

    assert comparison.delta.winner == "tie"
    assert comparison.delta.absolute_delta_points == 0.0
    assert comparison.delta.relative_lift_percent == 0.0
    assert "tied" in comparison.summary


def test_compare_videos_marks_comparison_unavailable_when_one_video_is_missing_metrics():
    video_a = make_video(label="A", views=1000, likes=90, comments=10)
    video_b = make_video(label="B", views=None, likes=45, comments=5)

    comparison = compare_videos(video_a, video_b)

    assert comparison.video_a.status == "available"
    assert comparison.video_b.status == "unavailable"
    assert comparison.delta.winner == "unavailable"
    assert comparison.delta.absolute_delta_points is None
    assert "unavailable until both videos" in comparison.summary


def test_relative_lift_is_none_when_loser_rate_is_zero():
    video_a = make_video(label="A", views=1000, likes=10, comments=0)
    video_b = make_video(label="B", views=1000, likes=0, comments=0)

    comparison = compare_videos(video_a, video_b)

    assert comparison.delta.winner == "A"
    assert comparison.delta.absolute_delta_points == 1.0
    assert comparison.delta.relative_lift_percent is None
    assert "undefined" in comparison.delta.explanation


def test_summarize_collection_is_batch_friendly():
    metrics = summarize_collection(
        [
            make_video(label="A", views=1000, likes=90, comments=10),
            make_video(label="B", views=500, likes=45, comments=5),
        ]
    )

    assert [metric.engagement_rate for metric in metrics] == [10.0, 10.0]
