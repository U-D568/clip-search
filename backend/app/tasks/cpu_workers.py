from multiprocessing.shared_memory import SharedMemory
import time
from typing import List

import cv2
import numpy as np

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


@celery_app.task(queue="dummy")
def dummy_queue_test(arg):
    print("sleep now")
    time.sleep(5)
    print(arg)
    print("Done")


@celery_app.task(queue="cpu_queue")
def frame_extractor(
    video_path: str, video_id: int, target_fps: float = 1.0, batch_size=32
):
    cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)

    imgs = []
    frames = []
    frame_progresses = []

    with MariaDBConnection.get_session() as session:
        # DB repositories
        frame_repo = FrameRepository(session)
        progress_repo = FrameProgressRepository(session)

        # frame time
        target_interval = 1.0 / target_fps
        last_time = -target_interval

        while True:
            ret, img = cap.read()
            if not ret:
                break

            current_time = (
                cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            )  # microsecends to seconds

            # extract frame every target_interval(about 1s)
            if current_time - last_time >= target_interval:
                last_time = current_time
                frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)

                # Frame instnace
                frame = Frame(video_key=video_id, timestamp=timestamp, index=frame_idx)
                frames.append(frame)

                # Frame progress instance
                progress = FrameProgress(status=FrameState.CREATED)
                progress.frame = frame
                frame_progresses.append(progress)

                imgs.append(img)

            # process batch
            if len(frames) >= batch_size:
                process_batch(
                    frames, frame_progresses, imgs, frame_repo, progress_repo, video_id
                )

        # process batch if frames are remained in the list
        if len(frames) > 0:
            process_batch(
                frames, frame_progresses, imgs, frame_repo, progress_repo, video_id
            )

    cap.release()


def process_batch(
    frames: List[Frame],
    progresses: List[FrameProgress],
    images: List[np.ndarray],
    frame_repo: FrameRepository,
    progress_repo: FrameProgressRepository,
    video_id: int,
):
    # Insert Frames to MariaDB
    try:
        frame_repo.add_all(frames)
        frame_repo.commit()
        progress_repo.add_all(progresses)
        progress_repo.commit()
    except:
        frame_repo.rollback()
        progress_repo.rollback()
        raise

    # init shared memory
    img_batch = np.stack(images)
    bsize = img_batch.nbytes
    shape = list(int(i) for i in img_batch.shape)
    dtype = str(img_batch.dtype)

    shm = SharedMemory(create=True, size=bsize)
    shm_array = np.ndarray(shape, dtype, buffer=shm.buf)

    # assign image to shared memory
    shm_array[:] = img_batch[:]

    frame_ids = [f.key for f in frames]

    # embedding task
    frame_embedding.delay(shm.name, shape, dtype, video_id, frame_ids)

    frames.clear()
    images.clear()
