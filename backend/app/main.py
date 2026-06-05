from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.container import AppContainer, build_app_container
from app.db.init_db import init_databases
from app.db.mongo import close_mongo
from app.db.qdrant import close_qdrant
from app.modules.chat.router import router as chat_router
from app.modules.comparisons.router import router as comparisons_router
from app.modules.streaming.router import router as streaming_router
from app.modules.video_ingestion.router import router as video_router


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_databases()
    container = await build_app_container()
    app.state.container = container
    app.state.comparison_repository = container.comparison_repository
    app.state.memory_store = container.memory_store
    app.state.retriever = container.retriever
    app.state.graph_runner = container.graph_runner
    app.state.chat_service = container.chat_service
    app.state.streaming_service = container.streaming_service
    app.state.analysis_service = container.analysis_service
    try:
        yield
    finally:
        container = getattr(app.state, "container", None)
        if isinstance(container, AppContainer):
            await container.close()
        await close_qdrant()
        await close_mongo()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.backend_cors_origins.split(",")
        if origin.strip()
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(video_router, prefix=settings.api_prefix)
app.include_router(comparisons_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(streaming_router)
