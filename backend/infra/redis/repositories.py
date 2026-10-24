from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator, List
from uuid import uuid4 as uuid

import redis
import redis.asyncio as async_redis
from redis.asyncio.client import PubSub

from infra.redis.schema import RedisQueryData
from utils.enums import VideoProgress, QueryProgress


class BaseVideoRepo:
    # pub/sub channel that notifies video state changes;
    # the state itself is stored in MariaDB
    def _channel(self, key: str):
        return f"video:{key}"


class VideoRedisRepository(BaseVideoRepo):
    def __init__(self, client: redis.Redis):
        self.client = client

    def publish_state(self, key: str, state: VideoProgress):
        self.client.publish(self._channel(key), state.value)


class AsyncRedisVideoRepository(BaseVideoRepo):
    def __init__(self, client: async_redis.Redis):
        self.client = client

    async def publish_state(self, key: str, state: VideoProgress):
        await self.client.publish(self._channel(key), state.value)

    async def _listen(pubsub: PubSub) -> AsyncIterator[VideoProgress]:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield VideoProgress(message["data"])

    @asynccontextmanager
    async def subscribe(self, key: str) -> AsyncGenerator[AsyncIterator[VideoProgress]]:
        channel = self._channel(key)
        pubsub = self.client.pubsub()

        try:
            await pubsub.subscribe(channel)
            yield self._listen()
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


class BaseQueryRepo:
    # hash key
    def _hkey(self, uuid: str):
        return f"query:{uuid}"

    # list key
    def _lkey(self, uuid: str):
        return f"response:{uuid}"

    def _init_state(self, owner_key: int, video_key: int) -> RedisQueryData:
        return RedisQueryData(
            video_key=video_key, owner_key=owner_key, state=QueryProgress.QUEUED.value
        )


class QueryRedisRepository(BaseQueryRepo):
    def __init__(self, client: redis.Redis):
        self.client = client

    def set_state(self, task_uuid: str, state: QueryProgress):
        hkey = self._hkey(task_uuid)
        self.client.hset(hkey, mapping={"state": state.value})
        self.client.expire(hkey, 600)

    def publish(self, task_uuid: str, state: QueryProgress):
        channel = self._hkey(task_uuid)
        self.client.publish(channel, state.value)

    def get_query(self, task_uuid: str) -> RedisQueryData:
        name = self._hkey(task_uuid)
        obj = self.client.hgetall(name)
        return RedisQueryData.model_validate(obj)

    def set_ids(self, task_uuid: str, ids: List[int]) -> None:
        list_key = self._lkey(task_uuid)
        self.client.delete(list_key)
        if ids:
            self.client.rpush(list_key, *ids)
        self.client.expire(list_key, 600)


class AsyncQueryReidsRepository(BaseQueryRepo):
    def __init__(self, client: async_redis.Redis):
        self.client = client

    async def register_query(self, video_key: int, owner_key: int) -> str:
        task_uuid = str(uuid())
        name = self._hkey(task_uuid)
        await self.client.hset(
            name, mapping=self._init_state(owner_key, video_key).model_dump()
        )
        await self.client.expire(name, 600)
        return task_uuid

    async def get_query(self, task_uuid: str) -> RedisQueryData:
        name = self._hkey(task_uuid)
        obj = await self.client.hgetall(name)
        return RedisQueryData.model_validate(obj)

    async def get_ids(self, task_uuid: str) -> List[int]:
        list_key = self._lkey(task_uuid)
        ids = await self.client.lrange(list_key, 0, -1)
        ids = list(map(int, ids))
        return ids

    async def subscribe(self, task_uuid: str) -> AsyncGenerator[QueryProgress, None]:
        key = self._hkey(task_uuid)
        pubsub = self.client.pubsub()
        try:
            await pubsub.subscribe(key)
            current_state = await self.client.hget(key, "state")
            if current_state is not None:
                state = QueryProgress(current_state)
                if state.is_terminal:
                    yield state
                    return

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                state = QueryProgress(message["data"])
                yield state
                if state.is_terminal:
                    break
        finally:
            await pubsub.unsubscribe(key)
            await pubsub.aclose()
