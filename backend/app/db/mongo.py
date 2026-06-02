from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings


_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client

    if _client is None:
        settings = get_settings()

        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            uuidRepresentation="standard",
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
        )

    return _client


def get_database() -> AsyncIOMotorDatabase:
    global _db

    if _db is None:
        settings = get_settings()
        _db = get_mongo_client()[settings.mongodb_db]

    return _db


async def ping_mongo() -> bool:
    try:
        await get_mongo_client().admin.command("ping")
        print("[MongoDB] Connected successfully")
        return True
    except Exception as exc:
        print(f"[MongoDB] Ping failed: {type(exc).__name__}: {exc}")
        return False


async def close_mongo() -> None:
    global _client, _db

    if _client is not None:
        _client.close()

    _client = None
    _db = None