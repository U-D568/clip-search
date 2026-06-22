import shutil
from typing import BinaryIO
from io import BytesIO

import cv2
import numpy as np
from fastapi import UploadFile

from app.exceptions import FileWriteException


def save_video_to_local(file: BinaryIO, save_path: str) -> str:
    try:
        with open(save_path, "w+b") as fp:
            shutil.copyfileobj(file, fp)
    except:
        raise FileWriteException()
    return save_path


def numpy_to_bytesio(array: np.ndarray, format=".png") -> BinaryIO:
    _, encoded = cv2.imencode(format, array)
    buffer = BytesIO(encoded.tobytes())
    return buffer


def UploadFile_to_bytesio(upload_file: UploadFile) -> BinaryIO:
    return upload_file.file
