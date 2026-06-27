import redis

from app.enums import VideoProgress


class RedisRepository:
    def __init__(self, client: redis.Redis):
        self.client = client

    def init_tracker(self, uuid: str):
        name = self._video_key(uuid)
        self.client.hset(
            name,
            mapping={
                "tasks": 0,
                "processed": 0,
                "state": VideoProgress.IN_PROGRESS.value,
            },
        )
        self.client.expire(name, 3600 * 3)

    def add_video_tasks(self, uuid: str, value: int):
        name = self._video_key(uuid)
        self.client.hincrby(name, "tasks", value)

    def add_video_processed(self, uuid: str, value: int):
        name = self._video_key(uuid)
        self.client.hincrby(name, "processed", value)

    def set_video_state(self, uuid: str, state: VideoProgress):
        name = self._video_key(uuid)
        self.client.hset(name, "state", state.value)
    
    def get_video_tasks(self, uuid: str):
        name = self._video_key(uuid)
        return self.client.hget(name, "tasks")
    
    def get_video_processed(self, uuid: str):
        name = self._video_key(uuid)
        return self.client.hget(name, "processed")

    def get_video_state(self, uuid: str) -> VideoProgress:
        name = self._video_key(uuid)
        state = self.client.hget(name, "state")
        return VideoProgress.from_string(state)
    
    def _video_key(self, key: str):
        return f"video-{key}"
    
    def _text_query_key(self, key: str):
        return f"query-{key}"
    
    def register_task(self, task_id: str, user_id: str):
        key = self._text_query_key(task_id)
        self.client.set(key, user_id)
        self.client.expire(key, 3600)
    
    def get_task_owner(self, task_id: str) -> str:
        key = self._text_query_key(task_id)
        return self.client.get(key)