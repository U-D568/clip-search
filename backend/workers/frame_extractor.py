import asyncio
import os

from infra.db.models import VideoProgress
from infra.db.repositories import AsyncFrameRepository, AsyncVideoRepository
from infra.db.connections import AsyncMariaDBConnection
from infra.db.models import Frame
from infra.s3.repositories import S3Repositories
from infra.s3.connections import S3Connection
from infra.redis.repositories import VideoRedisRepository
from infra.redis.connections import RedisConnection
from utils.frames import frame_generator, batch_generator
from utils.enums import VideoProgress
from workers.worker import celery_app
from workers.image_embedder import frame_embedding


@celery_app.task(queue="frame_extraction")
def frame_extractor(
    video_key: int, frame_interval: float = 1.0, batch_size=32
):
    # video_key: key of Video ORM
    # frame_interval: interval time between extracted frames
    # batch_size: length of frames to process in once.

    # initializations
    event_loop = asyncio.get_event_loop() # for async functions
    s3_client = S3Connection.get_client() # S3
    s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])
    redis_client = RedisConnection.get_client() # Reids
    redis_repo = VideoRedisRepository(redis_client)
    async_session = AsyncMariaDBConnection.get_session_context() # MariaDB
    frame_repo = AsyncFrameRepository(async_session)
    video_repo = AsyncVideoRepository(async_session)

    video = event_loop.run_until_complete(video_repo.find_by_id(video_key)) # video orm
    video_url = s3_repo.get_url(video.file_path)

    # publish message video is queued
    redis_repo.publish_state(video.uuid, VideoProgress.IN_PROGRESS)

    # frame extraction
    frame_gen = frame_generator(video_url, frame_interval, "jpg")

    # saves to db and redis
    batches = batch_generator(frame_gen, batch_size)
    for batch in batches:
        orm_frames = []
        s3_keys = []

        for item in batch:
            timestamp = item["timestamp"]
            index = item["index"]
            orm_frames.append(
                Frame(video_key=video_key, timestamp=timestamp, index=index)
            )

        try:
            frame_repo.add_all(orm_frames)
            event_loop.run_until_complete(frame_repo.commit())
        except:
            event_loop.run_until_complete(frame_repo.rollback())
            raise RuntimeError("Failed to insert Frame data to DB")

        # upload to s3 storage
        for i in range(len(orm_frames)):
            uuid = orm_frames[i].uuid
            s3_key = f"temp/{uuid}.jpg"
            s3_repo.upload(batch[i]["frame"], s3_key)
            s3_keys.append(s3_key)
        redis_repo.init_progress(video.uuid)
        redis_repo.add_extracted(video.uuid, len(batch))

        frame_ids = [f.key for f in orm_frames]
        frame_embedding.delay(s3_keys, video_key, frame_ids)
    redis_repo.set_state(video_key, VideoProgress.FRAME_COMPLETE)
