import redis

from utils.enums import VideoProgress


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

    def get_extracted(self, uuid: str):
        key = self._hkey(uuid)
        return self.client.hget(key, "extracted")

    def add_processed(self, uuid: str, value: int):
        key = self._hkey(uuid)
        self.client.hincrby(key, "processed", value)

    def get_processed(self, uuid: str):
        key = self._hkey(uuid)
        return self.client.hget(key, "processed")

    def set_state(self, uuid: str, state: VideoProgress):
        key = self._hkey(uuid)
        self.client.hset(key, "state", state.value)

    def get_state(self, uuid: str) -> VideoProgress:
        key = self._hkey(uuid)
        state = self.client.hget(key, "state")
        return VideoProgress(state)


class QueryRedisRepository:
    def __init__(self, client: redis.Redis):
        self.client = client

    def _hkey(self, uuid: str):
        return f"query-{uuid}"

    def register_task(self, task_id: str, user_id: str):
        key = self._hkey(task_id)
        self.client.set(key, user_id)
        self.client.expire(key, 3600)

    def get_task_owner(self, task_id: str) -> str:
        key = self._hkey(task_id)
        return self.client.get(key)
