"""Production dependency container for the FastAPI app."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.db.mongo import get_database
from app.modules.chat.service import ChatService, ChatServiceConfig
from app.modules.comparisons.service import (
    ChatServiceStreamer,
    ComparisonAnalysisService,
    MongoComparisonRepository,
    OpenAIResponseGenerator,
    ProductionGraphRunner,
    ProductionMemoryStore,
    ProductionRetriever,
)
from app.modules.graph.nodes import GraphDependencies
from app.modules.memory.service import MongoMemoryRepository
from app.modules.streaming.service import StreamingService
from app.modules.transcript_processing.service import TranscriptProcessingService
from app.modules.vector_store.schema import VectorStoreSettings
from app.modules.vector_store.service import VectorStoreService
from app.modules.video_ingestion.service import VideoIngestionService


@dataclass(slots=True)
class AppContainer:
    comparison_repository: MongoComparisonRepository
    memory_store: ProductionMemoryStore
    retriever: ProductionRetriever
    graph_runner: ProductionGraphRunner
    chat_service: ChatService
    streaming_service: StreamingService
    analysis_service: ComparisonAnalysisService
    vector_service: VectorStoreService

    async def close(self) -> None:
        await self.vector_service.close()


async def build_app_container() -> AppContainer:
    """Build concrete production services and prepare Qdrant for indexing/search."""

    settings = get_settings()
    db = get_database()

    vector_service = VectorStoreService(
        VectorStoreSettings(
            qdrant_url=settings.qdrant_url,
            qdrant_api_key=settings.qdrant_api_key,
            qdrant_collection=settings.qdrant_collection,
            openai_embedding_model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key or "",
            qdrant_vector_size=settings.embedding_dimension,
        )
    )
    await vector_service.startup()

    comparison_repository = MongoComparisonRepository(db)
    memory_store = ProductionMemoryStore(MongoMemoryRepository(db))
    retriever = ProductionRetriever(vector_service)
    response_generator = OpenAIResponseGenerator(api_key=settings.openai_api_key or "", model=settings.openai_chat_model)

    graph_runner = ProductionGraphRunner(
        GraphDependencies(
            retriever=retriever,
            metadata_repo=comparison_repository,
            memory_repo=memory_store,
            response_generator=response_generator,
            top_k_per_video=4,
        )
    )

    chat_service = ChatService(
        memory_store=memory_store,
        retriever=retriever,
        comparison_repository=comparison_repository,
        graph_runner=graph_runner,
        config=ChatServiceConfig(model_name=settings.openai_chat_model),
    )
    streaming_service = StreamingService(ChatServiceStreamer(chat_service), model_name=settings.openai_chat_model)
    analysis_service = ComparisonAnalysisService(
        repository=comparison_repository,
        ingestion_service=VideoIngestionService(),
        transcript_service=TranscriptProcessingService(),
        vector_service=vector_service,
    )

    return AppContainer(
        comparison_repository=comparison_repository,
        memory_store=memory_store,
        retriever=retriever,
        graph_runner=graph_runner,
        chat_service=chat_service,
        streaming_service=streaming_service,
        analysis_service=analysis_service,
        vector_service=vector_service,
    )
