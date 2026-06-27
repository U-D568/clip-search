import os

import redis


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
