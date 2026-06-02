from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings
from app.db.init_db import init_databases
from app.db.mongo import close_mongo
from app.db.qdrant import close_qdrant


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_databases()
    yield
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    health_router,
    prefix=settings.api_prefix,
)