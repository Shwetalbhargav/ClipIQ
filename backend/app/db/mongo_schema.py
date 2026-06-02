from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, OperationFailure

from app.db.mongo import get_database


COLLECTION_SCHEMAS = {
    "comparisons": {
        "bsonType": "object",
        "required": ["_id", "youtube_url", "instagram_url", "status", "created_at", "updated_at"],
        "properties": {
            "_id": {"bsonType": "string"},
            "youtube_url": {"bsonType": "string"},
            "instagram_url": {"bsonType": "string"},
            "normalized_youtube_url": {"bsonType": ["string", "null"]},
            "normalized_instagram_url": {"bsonType": ["string", "null"]},
            "status": {
                "enum": ["pending", "processing", "ready", "partial", "failed"]
            },
            "error": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    },

    "videos": {
        "bsonType": "object",
        "required": [
            "_id",
            "comparison_id",
            "video_label",
            "platform",
            "source_url",
            "created_at",
        ],
        "properties": {
            "_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "video_label": {"enum": ["A", "B"]},
            "platform": {"enum": ["youtube", "instagram"]},
            "source_url": {"bsonType": "string"},
            "platform_video_id": {"bsonType": ["string", "null"]},
            "creator": {"bsonType": ["string", "null"]},
            "creator_followers": {"bsonType": ["long", "int", "null"]},
            "title": {"bsonType": ["string", "null"]},
            "caption": {"bsonType": ["string", "null"]},
            "published_at": {"bsonType": ["date", "null"]},
            "duration_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "thumbnail_url": {"bsonType": ["string", "null"]},
            "hashtags": {"bsonType": "array"},
            "raw_metadata": {"bsonType": ["object", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    },

    "video_metrics": {
        "bsonType": "object",
        "required": ["_id", "video_id", "captured_at"],
        "properties": {
            "_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "video_id": {"bsonType": "string"},
            "views": {"bsonType": ["long", "int", "null"]},
            "likes": {"bsonType": ["long", "int", "null"]},
            "comments": {"bsonType": ["long", "int", "null"]},
            "shares": {"bsonType": ["long", "int", "null"]},
            "saves": {"bsonType": ["long", "int", "null"]},
            "engagement_rate": {"bsonType": ["double", "null"]},
            "engagement_formula": {"bsonType": "string"},
            "captured_at": {"bsonType": "date"},
        },
    },

    "transcript_segments": {
        "bsonType": "object",
        "required": ["_id", "comparison_id", "video_id", "segment_index", "text"],
        "properties": {
            "_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "video_id": {"bsonType": "string"},
            "segment_index": {"bsonType": "int"},
            "start_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "end_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "text": {"bsonType": "string"},
            "source_type": {
                "enum": [
                    "manual_caption",
                    "auto_caption",
                    "manual_captions",
                    "auto_captions",
                    "yt_dlp_captions",
                    "whisper",
                    "metadata_only",
                    "unknown",
                ]
            },
            "created_at": {"bsonType": "date"},
        },
    },

    "transcript_chunks": {
        "bsonType": "object",
        "required": [
            "_id",
            "comparison_id",
            "video_id",
            "chunk_index",
            "text",
            "embedding_model",
        ],
        "properties": {
            "_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "video_id": {"bsonType": "string"},
            "video_label": {"enum": ["A", "B"]},
            "platform": {"enum": ["youtube", "instagram"]},
            "chunk_index": {"bsonType": "int"},
            "start_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "end_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "text": {"bsonType": "string"},
            "qdrant_point_id": {"bsonType": ["string", "null"]},
            "embedding_model": {"bsonType": "string"},
            "metadata_version": {"bsonType": "int"},
            "created_at": {"bsonType": "date"},
        },
    },

    "chat_messages": {
        "bsonType": "object",
        "required": ["_id", "comparison_id", "role", "content", "created_at"],
        "properties": {
            "_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "role": {"enum": ["user", "assistant", "system"]},
            "content": {"bsonType": "string"},
            "status": {"enum": ["complete", "partial", "failed"]},
            "model": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
        },
    },

    "citations": {
        "bsonType": "object",
        "required": ["_id", "chat_message_id", "comparison_id", "citation_label"],
        "properties": {
            "_id": {"bsonType": "string"},
            "chat_message_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "video_id": {"bsonType": ["string", "null"]},
            "chunk_id": {"bsonType": ["string", "null"]},
            "citation_label": {"bsonType": "string"},
            "start_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "end_seconds": {"bsonType": ["double", "int", "long", "null"]},
            "quoted_text": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
        },
    },

    "extraction_jobs": {
        "bsonType": "object",
        "required": ["_id", "comparison_id", "status", "created_at", "updated_at"],
        "properties": {
            "_id": {"bsonType": "string"},
            "comparison_id": {"bsonType": "string"},
            "video_id": {"bsonType": ["string", "null"]},
            "job_type": {
                "enum": ["metadata", "transcript", "chunking", "embedding", "indexing"]
            },
            "status": {
                "enum": ["queued", "running", "succeeded", "failed", "retrying"]
            },
            "attempts": {"bsonType": "int"},
            "error": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    },
}


INDEXES = {
    "comparisons": [
        ([("created_at", DESCENDING)], {}),
        ([("status", ASCENDING)], {}),
    ],
    "videos": [
        ([("comparison_id", ASCENDING)], {}),
        ([("platform", ASCENDING), ("platform_video_id", ASCENDING)], {}),
        ([("creator", ASCENDING)], {}),
        ([("created_at", DESCENDING)], {}),
    ],
    "video_metrics": [
        ([("comparison_id", ASCENDING)], {}),
        ([("video_id", ASCENDING), ("captured_at", DESCENDING)], {}),
    ],
    "transcript_segments": [
        ([("comparison_id", ASCENDING), ("video_id", ASCENDING)], {}),
        ([("video_id", ASCENDING), ("segment_index", ASCENDING)], {"unique": True}),
    ],
    "transcript_chunks": [
        ([("comparison_id", ASCENDING), ("video_id", ASCENDING)], {}),
        ([("video_id", ASCENDING), ("chunk_index", ASCENDING)], {"unique": True}),
        ([("qdrant_point_id", ASCENDING)], {}),
    ],
    "chat_messages": [
        ([("comparison_id", ASCENDING), ("created_at", ASCENDING)], {}),
    ],
    "citations": [
        ([("chat_message_id", ASCENDING)], {}),
        ([("comparison_id", ASCENDING)], {}),
    ],
    "extraction_jobs": [
        ([("comparison_id", ASCENDING)], {}),
        ([("status", ASCENDING), ("updated_at", ASCENDING)], {}),
    ],
}


async def create_or_update_collection(name: str, schema: dict) -> None:
    db = get_database()

    existing_collections = await db.list_collection_names()

    if name in existing_collections:
        print(f"[MongoDB] Collection already exists, skipping validator update: {name}")
        return

    validator = {"$jsonSchema": schema}

    try:
        await db.create_collection(
            name,
            validator=validator,
            validationLevel="moderate",
        )
        print(f"[MongoDB] Created collection with validator: {name}")
    except CollectionInvalid:
        print(f"[MongoDB] Collection already exists after race, skipping: {name}")
    except OperationFailure as exc:
        print(f"[MongoDB] Could not create collection {name}: {exc}")
        raise


async def create_indexes(name: str) -> None:
    db = get_database()
    collection = db[name]

    for keys, options in INDEXES.get(name, []):
        await collection.create_index(keys, **options)


async def init_mongo_schema() -> None:
    for collection_name, schema in COLLECTION_SCHEMAS.items():
        await create_or_update_collection(collection_name, schema)
        await create_indexes(collection_name)
