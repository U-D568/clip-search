import os

import redis
import redis.asyncio as async_redis


class RedisConnection:
    _client = None

    @classmethod
    def init(cls):
        if cls._client is None:
            host = os.environ["REDIS_URL"]
            cls._client = redis.Redis(host=host, decode_responses=True)

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._client is None:
            raise RuntimeError("Redis Client is not initialized")
        return cls._client

    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None


class AsyncRedisConnection:
    _client = None

    @classmethod
    def init(cls):
        if cls._client is None:
            host = os.environ["REDIS_URL"]
            cls._client = async_redis.Redis(host=host, decode_responses=True)

    @classmethod
    def get_client(cls) -> async_redis.Redis:
        if cls._client is None:
            cls.init()
        return cls._client
