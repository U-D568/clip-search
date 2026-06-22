import io
import os
import subprocess
from typing import Iterable

import cv2
import numpy as np


def get_frame(video_path: str, timestamp: float):
    command = [
        "ffmpeg",
        "-ss",
        str(timestamp),
        "-i",
        video_path,
        "-vframes",
        "1",
        "-f",
        "image2",
        "-vcodec",
        "mjpeg",
        "-",
    ]

    try:
        # FFmpeg 프로세스 실행 및 바이트 데이터 가져오기
        process = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        image_bytes = process.stdout

        # 바이트 데이터를 메모리 파일 객체로 변환
        image_io = io.BytesIO(image_bytes)
        image_io.seek(0)

        # 사용자에게 파일 다운로드 형식으로 전송
        return image_io

    except subprocess.CalledProcessError as e:
        return f"FFmpeg error: {e.stderr.decode('utf-8')}", 500


def frame_generator(video_path: str, interval: float, format: str = "jpg"):
    FORMAT_MAP = {
        "jpg": {"codec": "mjpeg", "mime": "image/jpeg"},
        "png": {"codec": "png", "mime": "image/png"},
        "webp": {"codec": "libwebp", "mime": "image/webp"},
    }
    fps = 1 / interval

    # ffmpeg command
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-an"  # no audio
        "-i",  # input
        video_path,
        "-vf",
        f"fps={fps}",  # 1frame per seconds
        "-f",
        "image2pipe",  # push image to pipe
        "-vcodec",  # video codec
        FORMAT_MAP[format]["codec"],
        "-",  # print stdout
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=100 * (1 << 20),  # 100 MiB
    )

    buffer = b""
    timestamp = 0
    index = 0
    while True:
        chunk = proc.stdout.read(4096)  # 4KiB
        if not chunk:
            break
        buffer += chunk

        while (
            b"\xff\xd8" in buffer and b"\xff\xd9" in buffer
        ):  # multiple images can be in buffer
            start = buffer.index(b"\xff\xd8")
            end = buffer.index(b"\xff\xd9") + 2

            file_obj = io.BytesIO(buffer[start:end])
            buffer = buffer[end:]
            yield {"frame": file_obj, "timestamp": timestamp, "index": index}
            timestamp += interval
            index += 1


def batch_generator(iterable: Iterable, batch_size: int):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch.clear()
    if len(batch) > 0:
        yield batch


def bytes_to_numpy(bytesio: io.BytesIO) -> np.ndarray:
    file_bytes = np.frombuffer(bytesio.getvalue(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR_RGB)
    return image


if __name__ == "__main__":
    bytesio = get_frame("backend/test/long_penguin_video.mp4", 2)

    import sys
    import os

    cwd = os.getcwd()
    sys.path.append(f"{cwd}/backend")

    from app.s3.repositories import S3Repositories
    from app.s3.connections import S3Connection
    import dotenv

    dotenv.load_dotenv("backend/.env")
    S3Connection.init()
    s3_client = S3Connection.get_client()
    s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])
    s3_repo.upload(bytesio, "test.jpg")
    print(1)
