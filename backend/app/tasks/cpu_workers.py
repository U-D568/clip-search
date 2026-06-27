import os

from app.db.models import VideoProgress
from app.db.repositories import (
    FrameRepository,
)
from app.db.connections import MariaDBConnection
from app.tasks.worker import celery_app
from app.tasks.gpu_workers import frame_embedding
from app.db.models import Frame
from app.s3.repositories import S3Repositories
from app.s3.connections import S3Connection
from app.redis.repositories import RedisRepository
from app.redis.connections import RedisConnection
from app.utils.frames import frame_generator, batch_generator
from app.enums import VideoProgress


@celery_app.task(queue="cpu_queue")
def frame_extractor(
    video_path: str, video_id: int, interval: float = 1.0, batch_size=32
):
    # init repositories
    s3_client = S3Connection.get_client()
    s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])
    redis_client = RedisConnection.get_client()
    redis_repo = RedisRepository(redis_client)

    video_url = s3_repo.get_url(video_path)
    frame_gen = frame_generator(video_url, interval, "jpg")
    batches = batch_generator(frame_gen, batch_size)

    with MariaDBConnection.get_session() as session:
        # DB repositories
        frame_repo = FrameRepository(session)

        for batch in batches:
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
                s3_repo.upload(batch[i]["frame"], s3_key)
                s3_keys.append(s3_key)
            redis_repo.init_tracker(video_id)
            redis_repo.add_video_tasks(video_id, len(batch))

            frame_ids = [f.key for f in frames]
            frame_embedding.delay(s3_keys, video_id, frame_ids)
        redis_repo.set_video_state(video_id, VideoProgress.FRAME_COMPLETE)
