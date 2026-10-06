from pydantic import BaseModel

from utils.enums import QueryProgress


class RedisQueryData(BaseModel):
    video_key: int
    owner_key: int
    state: QueryProgress = QueryProgress.QUEUED