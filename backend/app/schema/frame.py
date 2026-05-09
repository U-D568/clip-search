from dataclasses import dataclass
from typing import List

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
