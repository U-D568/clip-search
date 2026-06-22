from multiprocessing.shared_memory import SharedMemory
import time
from typing import List, Iterable
import subprocess
import os
import io

import numpy as np
import redis

from app.enums import FrameState
from app.db.models import VideoProgress, FrameProgress
from app.db.repositories import (
    VideoProgressRepository,
    FrameRepository,
    FrameProgressRepository,
)
from app.db.connections import MariaDBConnection
from app.tasks.worker import celery_app
from app.tasks.gpu_workers import frame_embedding
from app.db.models import Frame
from app.s3.repositories import S3Repositories
from app.s3.connections import S3Connection
from app.utils.file import numpy_to_bytesio
from app.utils.frames import frame_generator, batch_generator


@celery_app.task(queue="cpu_queue")
def frame_extractor(
    video_path: str, video_id: int, interval: float = 1.0, batch_size=32
):
    # test code
    video_path = "videos/30fd27cb-cf54-46f2-8624-8bf13a94a09a.mp4"
    frame_gen = frame_generator(video_path, interval, "jpg")
    batches = batch_generator(frame_gen, batch_size)

    with MariaDBConnection.get_session() as session:
        # DB repositories
        frame_repo = FrameRepository(session)
        s3_client = S3Connection.get_client()
        s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])

        for batch in batches:
            images = [item["frame"] for item in batch]
            frames = []
            s3_keys = []

            for item in batch:
                timestamp = item["timestamp"]
                index = item["index"]
                frames.append(
                    Frame(video_key=video_id, timestamp=timestamp, index=index)
                )
            
            try:
                frame_repo.add_all(frames)
                frame_repo.commit()
            except:
                frame_repo.rollback()
                raise
            
            # upload to s3 storage
            for i in range(len(frames)):
                uuid = frames[i].uuid
                s3_key = f"temp/{uuid}.jpg"
                bytesio = numpy_to_bytesio(images[i], ".jpg")
                s3_repo.upload(bytesio, s3_key)
                s3_keys.append(s3_key)
            
            frame_ids = [f.id for f in frames]
            frame_embedding.delay(s3_keys, video_id, frame_ids)
