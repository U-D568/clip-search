from typing import AsyncGenerator, List
from uuid import uuid4 as uuid

import redis
import redis.asyncio as async_redis

from infra.redis.schema import RedisQueryData
from utils.enums import VideoProgress, QueryProgress


class VideoRedisRepository:
    def __init__(self, client: redis.Redis):
        self.client = client

    def _hkey(self, uuid: str):
        return f"video-{uuid}"

    def init_progress(self, uuid: str):
        name = self._hkey(uuid)
        self.client.hset(
            name,
            mapping={
                "tasks": 0,
                "processed": 0,
                "state": VideoProgress.IN_PROGRESS.value,
            },
        )
        self.client.expire(name, 3600 * 3)

    def add_extracted(self, uuid: str, value: int):
        key = self._hkey(uuid)
        self.client.hincrby(key, "extracted", value)

    def get_extracted(self, uuid: str) -> int:
        key = self._hkey(uuid)
        return int(self.client.hget(key, "extracted"))

    def add_processed(self, uuid: str, value: int):
        key = self._hkey(uuid)
        self.client.hincrby(key, "processed", value)

    def get_processed(self, uuid: str) -> int:
        key = self._hkey(uuid)
        return int(self.client.hget(key, "processed"))

    def set_state(self, uuid: str, state: VideoProgress):
        key = self._hkey(uuid)
        self.client.hset(key, "state", state.value)

    def get_state(self, uuid: str) -> VideoProgress:
        key = self._hkey(uuid)
        state = self.client.hget(key, "state")
        return VideoProgress(state)

    def publish_state(self, uuid: str, state: VideoProgress):
        channel = self._hkey(uuid)
        self.client.publish(channel, state.value)


class AsyncRedisVideoRepository:
    def __init__(self, client: async_redis.Redis):
        self.client = client

    def _hkey(self, uuid: str):
        return f"video-{uuid}"

    async def subscribe(self, uuid: str) -> AsyncGenerator[VideoProgress, None]:
        key = self._hkey(uuid)

        current_state = await self.client.hget(key, "processed")
        if current_state is None:
            return  # raise exception here

        current_state = VideoProgress(current_state)
        if current_state == VideoProgress.COMPLETE:
            yield current_state
            return

        pubsub = self.client.pubsub()
        try:
            await pubsub.subscribe(key)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                state = VideoProgress(message["data"])
                if state == VideoProgress.COMPLETE:
                    yield state
                    break
                yield state
        finally:
            pubsub.unsubscribe()
            pubsub.close()


class BaseQueryRedisRepository:
    # hash's key
    def _hkey(self, uuid: str):
        return f"query-{uuid}"

    # list's key
    def _lkey(self, uuid: str):
        return f"query-list-{uuid}"

    def _init_state(self, user_uuid: str, video_uuid: str) -> RedisQueryData:
        return RedisQueryData(video_uuid, user_uuid, QueryProgress.QUEUED.value)


class QueryRedisRepository(BaseQueryRedisRepository):
    def __init__(self, client: redis.Redis):
        self.client = client

    def register_query(self, video_uuid: str, user_uuid: str):
        name = self._hkey(video_uuid)
        self.client.hset(
            name, mapping=self._init_state(user_uuid, video_uuid).model_dump()
        )
        self.client.expire(name, 600)

    def get_task_owner(self, task_id: str) -> str:
        key = self._hkey(task_id)
        return self.client.get(key)


class AsyncQueryReidsRepository(BaseQueryRedisRepository):
    def __init__(self, client: async_redis.Redis):
        self.client = client

    async def register_query(self, video_uuid: str, user_uuid: str) -> str:
        task_uuid = uuid()
        name = self._hkey(task_uuid)
        await self.client.hset(name, mapping=self._init_state(user_uuid, video_uuid))
        await self.client.expire(name, 600)
        return task_uuid

    async def get_query(self, task_uuid: str) -> RedisQueryData:
        name = self._hkey(task_uuid)
        obj = await self.client.hgetall(name)
        return RedisQueryData(obj["video"], obj["owner"], QueryProgress(obj["state"]))

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
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                state = QueryProgress(message["data"])
                if state == QueryProgress.COMPLETE:
                    yield state
                    break
                yield state
        finally:
            pubsub.unsubscribe()
            pubsub.close()
