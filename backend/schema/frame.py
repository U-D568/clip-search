from dataclasses import dataclass
from typing import List, Optional, Any

import numpy as np
from pydantic import BaseModel


@dataclass
class ExtractedFrame:
    timestamp: float
    index: int
    array: np.ndarray


@dataclass
class BatchedFrames:
    array: np.ndarray
    frames: List[ExtractedFrame]


class QdrantPoint(BaseModel):
    id: int
    vector: List[float]
    metadata: "PointMetadata"


class PointMetadata(BaseModel):
    video_key: int
    frame_key: int
    timestamp: float
    index: int
