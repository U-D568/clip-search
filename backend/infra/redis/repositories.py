from typing import AsyncGenerator, List, Optional
from uuid import uuid4 as uuid

import redis
import redis.asyncio as async_redis

from infra.redis.schema import RedisQueryData
from utils.enums import VideoProgress, QueryProgress


class BaseVideoRepo:
    def _hkey(self, key: str):
        return f"video:{key}"


class VideoRedisRepository(BaseVideoRepo):
    def __init__(self, client: redis.Redis):
        self.client = client

    def init_progress(self, key: str):
        name = self._hkey(key)
        self.client.hset(
            name,
            mapping={
                "tasks": 0,
                "processed": 0,
            },
        )
        self.client.hsetnx(name, "state", VideoProgress.IN_PROGRESS.value)
        self.client.expire(name, 3600 * 3)

    def add_extracted(self, key: str, value: int):
        redis_key = self._hkey(key)
        self.client.hincrby(redis_key, "extracted", value)

    def get_extracted(self, key: str) -> int:
        redis_key = self._hkey(key)
        return int(self.client.hget(redis_key, "extracted"))

    def add_processed(self, key: str, value: int):
        redis_key = self._hkey(key)
        self.client.hincrby(redis_key, "processed", value)

    def get_processed(self, key: str) -> int:
        redis_key = self._hkey(key)
        return int(self.client.hget(redis_key, "processed"))

    def set_state(self, key: str, state: VideoProgress):
        redis_key = self._hkey(key)
        self.client.hset(redis_key, "state", state.value)
        self.client.expire(redis_key, 3600 * 3)

    def get_state(self, key: str) -> Optional[VideoProgress]:
        redis_key = self._hkey(key)
        state = self.client.hget(redis_key, "state")
        return VideoProgress(state) if state is not None else None

    def set_state_if_not_aborted(self, key: str, state: VideoProgress) -> bool:
        redis_key = self._hkey(key)
        script = """
        local current = redis.call('HGET', KEYS[1], 'state')
        if not current or current == ARGV[1] then
            return 0
        end
        redis.call('HSET', KEYS[1], 'state', ARGV[2])
        redis.call('EXPIRE', KEYS[1], ARGV[3])
        return 1
        """
        updated = self.client.eval(
            script,
            1,
            redis_key,
            VideoProgress.ABORTED.value,
            state.value,
            3600 * 3,
        )
        return bool(updated)

    def publish_state(self, key: str, state: VideoProgress):
        channel = self._hkey(key)
        self.client.publish(channel, state.value)


class AsyncRedisVideoRepository(BaseVideoRepo):
    def __init__(self, client: async_redis.Redis):
        self.client = client

    async def set_state(self, key: str, state: VideoProgress):
        redis_key = self._hkey(key)
        await self.client.hset(redis_key, "state", state.value)
        await self.client.expire(redis_key, 3600 * 3)

    async def publish_state(self, key: str, state: VideoProgress):
        await self.client.publish(self._hkey(key), state.value)

    async def delete_progress(self, key: str):
        redis_key = self._hkey(key)
        await self.client.delete(redis_key)

    async def subscribe(self, key: str) -> AsyncGenerator[VideoProgress, None]:
        redis_key = self._hkey(key)

        current_state = await self.client.hget(redis_key, "state")
        if current_state is None:
            return  # raise exception here

        current_state = VideoProgress(current_state)
        if current_state in {
            VideoProgress.COMPLETE,
            VideoProgress.ABORTED,
            VideoProgress.ERROR,
        }:
            yield current_state
            return

        pubsub = self.client.pubsub()
        try:
            await pubsub.subscribe(redis_key)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                state = VideoProgress(message["data"])
                if state in {
                    VideoProgress.COMPLETE,
                    VideoProgress.ABORTED,
                    VideoProgress.ERROR,
                }:
                    yield state
                    break
                yield state
        finally:
            await pubsub.unsubscribe(redis_key)
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
        task_uuid = uuid()
        name = self._hkey(task_uuid)
        await self.client.hset(name, mapping=self._init_state(owner_key, video_key).model_dump())
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
                if state in {QueryProgress.COMPLETE, QueryProgress.ERROR}:
                    yield state
                    return

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                state = QueryProgress(message["data"])
                if state in {QueryProgress.COMPLETE, QueryProgress.ERROR}:
                    yield state
                    break
                yield state
        finally:
            await pubsub.unsubscribe(key)
            await pubsub.aclose()
