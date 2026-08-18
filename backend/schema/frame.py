from dataclasses import dataclass
from typing import List, Optional, Any

import numpy as np


@dataclass
class ExtractedFrame:
    timestamp: float
    index: int
    array: np.ndarray


@dataclass
class BatchedFrames:
    array: np.ndarray
    frames: List[ExtractedFrame]


@dataclass
class QdrantPoint:
    id: int
    vector: List[float]
    payload: Optional[Any]

    def to_dict(self):
        return {"id": self.id, "vector": self.vector, "payload": self.payload}


@dataclass
class FrameMetadata:
    video_key: int
    frame_key: int
    timestamp: float
    index: int

    def to_dict(self):
        return {
            "video_key": self.video_key,
            "frame_key": self.frame_key,
            "timestamp": self.timestamp,
            "index": self.index,
        }
