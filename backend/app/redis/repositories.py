import redis

from app.enums import VideoProgress


class RedisRepository:
    def __init__(self, client: redis.Redis):
        self.client = client

    def init_tracker(self, uuid: str):
        self.client.hset(
            uuid,
            mapping={
                "tasks": 0,
                "processed": 0,
                "state": VideoProgress.IN_PROGRESS.value,
            },
        )
        self.client.expire(uuid, 3600 * 3)

    def add_video_tasks(self, uuid: str, value: int):
        self.client.hincrby(uuid, "tasks", value)

    def add_video_processed(self, uuid: str, value: int):
        self.client.hincrby(uuid, "processed", value)

    def set_video_state(self, uuid: str, state: VideoProgress):
        self.client.hset(uuid, "state", state.value)
    
    def get_video_tasks(self, uuid: str):
        return self.client.hget(uuid, "tasks")
    
    def get_video_processed(self, uuid: str):
        return self.client.hget(uuid, "processed")

    def get_video_state(self, uuid: str):
        state = self.client.hget(uuid, "state")
        if state == VideoProgress.IN_PROGRESS.value:
            return VideoProgress.IN_PROGRESS
        elif state == VideoProgress.QUEUED.value:
            return VideoProgress.QUEUED
        elif state == VideoProgress.FRAME_COMPLETE.value:
            return VideoProgress.FRAME_COMPLETE
        elif state == VideoProgress.COMPLETE.value:
            return VideoProgress.COMPLETE
        else:
            return VideoProgress.ERROR
