from app.core.config import get_settings
from app.db.mongo import ping_mongo
from app.db.mongo_schema import init_mongo_schema
from app.db.qdrant import ping_qdrant, init_qdrant_collection


async def init_databases() -> None:
    settings = get_settings()

    print(f"[Startup] MongoDB DB: {settings.mongodb_db}")
    print(f"[Startup] Qdrant URL: {settings.qdrant_url}")

    mongo_ok = await ping_mongo()
    if not mongo_ok:
        raise RuntimeError(
            "MongoDB connection failed. Check Atlas IP allowlist, username, password, "
            "MONGODB_URI spelling, and whether the .env file is inside backend/."
        )

    await init_mongo_schema()
    print("[Startup] MongoDB schema initialized")

    qdrant_ok = await ping_qdrant()
    if not qdrant_ok:
        print("[Startup] Qdrant unavailable. Skipping Qdrant initialization for now.")
        return

    await init_qdrant_collection()
    print("[Startup] Qdrant collection initialized")