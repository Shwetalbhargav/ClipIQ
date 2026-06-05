from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.comparisons.schema import ComparisonAnalyzeRequest
from app.modules.comparisons.service import ComparisonAnalysisService, MongoComparisonRepository, mongo_transcript_source_type
from app.modules.transcript_processing.schema import (
    TranscriptChunk,
    TranscriptExtractionResult,
    TranscriptSegment,
    TranscriptSource,
    TranscriptStatus,
)
from app.modules.vector_store.schema import IndexedVector
from app.modules.video_ingestion.schema import (
    MetricValue,
    NormalizedVideoMetadata,
    SupportedPlatform,
    VideoAnalysisItem,
    VideoAnalyzeResponse,
)


class FakeRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.comparison = {}
        self.videos = []
        self.metrics = []
        self.chunks = []

    async def create_comparison(self, **kwargs):
        self.calls.append("create_comparison")
        self.comparison = {
            "_id": kwargs["comparison_id"],
            "status": "processing",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    async def save_video(self, **kwargs):
        self.calls.append(f"save_video_{kwargs['label']}")
        doc_id = f"{kwargs['comparison_id']}:{kwargs['label']}"
        metadata = kwargs["metadata"]
        self.videos.append(
            {
                "_id": doc_id,
                "video_label": kwargs["label"],
                "platform": metadata.platform.value,
                "source_url": str(metadata.source_url),
                "platform_video_id": metadata.video_id,
                "creator": metadata.creator,
                "creator_followers": metadata.follower_count.value,
                "title": metadata.title,
                "hashtags": metadata.hashtags,
            }
        )
        return doc_id

    async def save_metric(self, **kwargs):
        self.calls.append("save_metric")
        metadata = kwargs["metadata"]
        self.metrics.append(
            {
                "video_id": kwargs["video_doc_id"],
                "views": metadata.views.value,
                "likes": metadata.likes.value,
                "comments": metadata.comments.value,
                "engagement_rate": kwargs["engagement_rate"],
            }
        )

    async def save_transcript_result(self, **kwargs):
        self.calls.append("save_transcript_result")
        for chunk in kwargs["result"].chunks:
            self.chunks.append(
                {
                    "_id": f"{kwargs['video_doc_id']}:chunk:{chunk.chunk_index}",
                    "video_label": kwargs["label"],
                    "qdrant_point_id": None,
                }
            )

    async def update_chunk_point_ids(self, *, updates):
        self.calls.append("update_chunk_point_ids")
        by_id = {item["_id"]: item for item in self.chunks}
        for update in updates:
            by_id[update["chunk_doc_id"]]["qdrant_point_id"] = update["point_id"]

    async def update_comparison(self, **kwargs):
        self.calls.append("update_comparison")
        self.comparison.update(
            {
                "status": kwargs["status"],
                "errors": kwargs["errors"],
                "updated_at": datetime.now(timezone.utc),
            }
        )

    async def get_comparison(self, comparison_id):
        return {
            "comparison": self.comparison,
            "videos": self.videos,
            "metrics": self.metrics,
            "chunks": self.chunks,
        }


class PyMongoLikeDatabase(dict):
    def __bool__(self):
        raise NotImplementedError("Database objects do not implement truth value testing")


class FakeIngestionService:
    def __init__(self) -> None:
        self.called = False

    async def analyze_videos(self, urls):
        self.called = True
        return VideoAnalyzeResponse(
            status="completed",
            videos=[
                VideoAnalysisItem(label="A", metadata=metadata("yt-native", SupportedPlatform.YOUTUBE, urls[0], 1000, 90, 10)),
                VideoAnalysisItem(label="B", metadata=metadata("ig-native", SupportedPlatform.INSTAGRAM, urls[1], 2000, 70, 10)),
            ],
            errors=[],
        )


class FakeTranscriptService:
    def __init__(self) -> None:
        self.calls = []

    def process(self, request):
        self.calls.append(request)
        return TranscriptExtractionResult(
            video_id=request.video_id,
            status=TranscriptStatus.READY,
            source_type=TranscriptSource.AUTO_CAPTIONS,
            segments=[
                TranscriptSegment(
                    segment_index=0,
                    text=f"{request.video_id} hook in first five seconds",
                    start_seconds=0,
                    end_seconds=5,
                    source_type=TranscriptSource.AUTO_CAPTIONS,
                )
            ],
            chunks=[
                TranscriptChunk(
                    chunk_index=0,
                    text=f"{request.video_id} hook in first five seconds",
                    start_seconds=0,
                    end_seconds=5,
                    segment_indices=[0],
                    source_type=TranscriptSource.AUTO_CAPTIONS,
                )
            ],
        )


class FakeVectorService:
    def __init__(self) -> None:
        self.calls = []
        self.settings = type("Settings", (), {"openai_embedding_model": "test-embedding"})()

    async def index_chunks(self, chunks):
        self.calls.append(chunks)
        return [
            IndexedVector(
                point_id=f"point-{chunk.metadata.video_id}-{chunk.metadata.chunk_index}",
                comparison_id=chunk.metadata.comparison_id,
                video_id=chunk.metadata.video_id,
                chunk_id=chunk.metadata.chunk_id,
                chunk_index=chunk.metadata.chunk_index,
            )
            for chunk in chunks
        ]


def metadata(video_id, platform, source_url, views, likes, comments):
    return NormalizedVideoMetadata(
        video_id=video_id,
        platform=platform,
        source_url=source_url,
        canonical_url=source_url,
        creator=f"creator-{video_id}",
        follower_count=MetricValue.available(1000),
        title=f"title-{video_id}",
        views=MetricValue.available(views),
        likes=MetricValue.available(likes),
        comments=MetricValue.available(comments),
        hashtags=["demo"],
        upload_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_comparison_service_runs_end_to_end_with_fakes() -> None:
    repo = FakeRepository()
    ingestion = FakeIngestionService()
    transcript = FakeTranscriptService()
    vector = FakeVectorService()
    service = ComparisonAnalysisService(
        repository=repo,
        ingestion_service=ingestion,
        transcript_service=transcript,
        vector_service=vector,
    )

    response = await service.analyze(
        ComparisonAnalyzeRequest(
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            instagram_url="https://www.instagram.com/reel/CxYz123abcd/",
        )
    )

    assert response.status == "ready"
    assert response.video_a.platform == "youtube"
    assert response.video_b.platform == "instagram"
    assert response.video_a.engagement_rate == 10.0
    assert response.video_b.engagement_rate == 4.0
    fetched = await service.get(response.comparison_id)
    assert fetched.engagement["video_a"]["engagement_rate"] == 10.0
    assert fetched.engagement["video_b"]["engagement_rate"] == 4.0
    assert fetched.transcript_status == {"A": "ready", "B": "ready"}
    assert ingestion.called is True
    assert [call.video_id for call in transcript.calls] == ["A", "B"]
    assert len(vector.calls) == 2
    assert "save_transcript_result" in repo.calls
    assert "update_chunk_point_ids" in repo.calls


def test_mongo_repository_does_not_truth_test_database() -> None:
    db = PyMongoLikeDatabase()

    repo = MongoComparisonRepository(db)

    assert repo.db is db


def test_mongo_transcript_source_type_supports_legacy_validators() -> None:
    assert mongo_transcript_source_type(TranscriptSource.MANUAL_CAPTIONS) == "manual_caption"
    assert mongo_transcript_source_type(TranscriptSource.AUTO_CAPTIONS) == "auto_caption"
    assert mongo_transcript_source_type(TranscriptSource.YT_DLP_CAPTIONS) == "auto_caption"
    assert mongo_transcript_source_type(TranscriptSource.WHISPER) == "whisper"
