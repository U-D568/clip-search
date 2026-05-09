from typing import List, Optional, Any
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class QdrantPoint:
    id: int
    vector: List[float]
    payload: Optional[Any]

    def to_dict(self):
        return {"id": self.id, "vector": self.vector, "payload": self.payload}


@dataclass
class FrameMeta:
    video_id: int
    frame_id: int
    timestamp: float
    index: int

    def to_dict(self):
        return {
            "video_id": self.video_id,
            "timestamp": self.timestamp,
            "index": self.index,
        }


class LoginRequest(BaseModel):
    username: str
    password: str
