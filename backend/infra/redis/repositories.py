from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator, AsyncIterator, Awaitable, Callable, List, Optional
from uuid import uuid4 as uuid

import redis.asyncio as async_redis
from redis.asyncio.client import Pipeline, PubSub

from infra.redis.schema import RedisQueryData
from utils.enums import VideoProgress, QueryProgress


class BaseVideoRepo:
    def _hkey(self, key: str):
        return f"video:{key}"

    # pub/sub channel that notifies video state changes
    def _channel(self, key: str):
        return f"video:{key}:state"


class AsyncRedisVideoRepository(BaseVideoRepo):
    def __init__(self, client: async_redis.Redis):
        self.client = client
        self.VIDEO_EXPIRE = int(os.environ.get("VIDEO_EXPIRE", "10800"))

    async def abort(self, key: str):
        await self.set_state(key, VideoProgress.ABORTED)

    async def publish_state(self, key: str, state: VideoProgress):
        await self.client.publish(self._channel(key), state.value)

    @staticmethod
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
            yield self._listen(pubsub)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def init_progress(self, key: str) -> VideoProgress:
        redis_key = self._hkey(key)

        await self.client.hset(
            redis_key,
            mapping={
                "state": VideoProgress.IN_PROGRESS.value,
                "extracted": 0,
                "processed": 0,
            },
        )
        await self.client.expire(redis_key, self.VIDEO_EXPIRE)

    async def add_extracted(self, key: str, value: int) -> VideoProgress:
        redis_key = self._hkey(key)
        await self.client.hincrby(redis_key, "extracted", value)
        await self.client.expire(redis_key, self.VIDEO_EXPIRE)
        return await self.get_state(redis_key)

    # Counts embedded frames; EXTRACTED -> COMPLETE when the counts match.
    async def add_processed(self, key: str, value: int) -> VideoProgress:
        redis_key = self._hkey(key)

        await self.client.hincrby(redis_key, "extracted", value)
        extracted, processed = await self.client.hmget(
            redis_key, "extracted", "processed"
        )

        state = await self.get_state(redis_key)
        if state == VideoProgress.EXTRACTED and int(processed) == int(extracted):
            state = VideoProgress.COMPLETE
            await self.client.hset(redis_key, "state", state.value)

        return state

    async def get_extracted(self, key: str) -> int:
        redis_key = self._hkey(key)
        count = await self.client.hget(redis_key, "extracted")
        if count is None:
            return -1
        return int(count)

    async def get_processed(self, key: str) -> int:
        redis_key = self._hkey(key)
        count = await self.client.hget(redis_key, "processed")
        if count is None:
            return -1
        return int(count)

    async def set_state(self, key: str, state: VideoProgress):
        redis_key = self._hkey(key)
        await self.client.hset(redis_key, "state", state.value)
        await self.client.expire(redis_key, self.VIDEO_EXPIRE)

    async def get_state(self, key: str) -> VideoProgress:
        redis_key = self._hkey(key)
        state = await self.client.hget(redis_key, "state")
        if state is None:
            return VideoProgress.ERROR
        return VideoProgress(state)


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


class AsyncRedisQueryRepository(BaseQueryRepo):
    def __init__(self, client: async_redis.Redis):
        self.client = client
        self.QUERY_EXPIRE = int(os.environ.get("QUERY_EXPIRE", "600"))

    async def register_query(self, video_key: int, owner_key: int) -> str:
        task_uuid = str(uuid())
        name = self._hkey(task_uuid)
        # mode="json" stores the enum as its string value
        await self.client.hset(
            name, mapping=self._init_state(owner_key, video_key).model_dump(mode="json")
        )
        await self.client.expire(name, self.QUERY_EXPIRE)
        return task_uuid

    async def get_query(self, task_uuid: str) -> RedisQueryData:
        name = self._hkey(task_uuid)
        obj = await self.client.hgetall(name)
        return RedisQueryData.model_validate(obj)

    async def set_state(self, task_uuid: str, state: QueryProgress):
        hkey = self._hkey(task_uuid)
        await self.client.hset(hkey, mapping={"state": state.value})
        await self.client.expire(hkey, self.QUERY_EXPIRE)

    async def publish(self, task_uuid: str, state: QueryProgress):
        channel = self._hkey(task_uuid)
        await self.client.publish(channel, state.value)

    async def set_ids(self, task_uuid: str, ids: List[int]) -> None:
        list_key = self._lkey(task_uuid)
        await self.client.delete(list_key)
        if ids:
            await self.client.rpush(list_key, *ids)
        await self.client.expire(list_key, self.QUERY_EXPIRE)

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
