from pydantic import BaseModel

from utils.enums import QueryProgress


class RedisQueryData(BaseModel):
    video: str # video uuid
    owner: str # user uuid
    state: QueryProgress = QueryProgress.QUEUED