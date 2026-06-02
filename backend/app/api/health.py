from fastapi import APIRouter

from app.core.config import get_settings
from app.db.mongo import ping_mongo
from app.db.qdrant import ping_qdrant


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    settings = get_settings()

    mongo_ok = await ping_mongo()
    qdrant_ok = await ping_qdrant()

    overall_status = "ok" if mongo_ok and qdrant_ok else "degraded"

    return {
        "status": overall_status,
        "service": settings.app_name,
        "environment": settings.app_env,
        "services": {
            "mongodb": "ok" if mongo_ok else "down",
            "qdrant": "ok" if qdrant_ok else "down",
        },
    }