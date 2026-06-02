from app.db.mongo import ping_mongo
from app.db.mongo_schema import init_mongo_schema
from app.db.qdrant import ping_qdrant, init_qdrant_collection


async def init_databases() -> None:
    mongo_ok = await ping_mongo()
    if not mongo_ok:
        raise RuntimeError("MongoDB connection failed")

    qdrant_ok = await ping_qdrant()
    if not qdrant_ok:
        raise RuntimeError("Qdrant connection failed")

    await init_mongo_schema()
    await init_qdrant_collection()