import os

import redis.asyncio as async_redis


class RedisConnection:
    _client = None

    @classmethod
    def init(cls):
        if cls._client is None:
            host = os.environ["REDIS_URL"]
            cls._client = async_redis.Redis(host=host, decode_responses=True)

    @classmethod
    def get_client(cls) -> async_redis.Redis:
        if cls._client is None:
            raise RuntimeError("Redis Client is not initialized")
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.aclose()
            cls._client = None
