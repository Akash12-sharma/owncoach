from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import settings

_client: AsyncIOMotorClient = None


async def get_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = settings.get_mongo_client()
    return _client[settings.MONGODB_DB]
