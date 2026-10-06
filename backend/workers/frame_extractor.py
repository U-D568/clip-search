import asyncio
import os

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
from workers.tasks import frame_embedding


@celery_app.task(queue="extraction_queue")
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

    video = event_loop.run_until_complete(video_repo.find_by_id(video_key))
    if video is None:
        return

    current_state = event_loop.run_until_complete(
        video_repo.get_state_by_id(video_key)
    )
    if current_state is None or current_state == VideoProgress.ABORTED:
        return

    if not event_loop.run_until_complete(
        video_repo.set_state_if_not_aborted(video_key, VideoProgress.IN_PROGRESS)
    ):
        event_loop.run_until_complete(video_repo.rollback())
        return
    event_loop.run_until_complete(video_repo.commit())

    video_url = s3_repo.get_url(video.file_path)
    redis_key = str(video.key)
    redis_repo.init_progress(redis_key)
    redis_repo.publish_state(redis_key, VideoProgress.IN_PROGRESS)

    created_frame_ids = []
    created_frame_uuids = []

    def should_continue():
        state = event_loop.run_until_complete(video_repo.get_state_by_id(video_key))
        return state is not None and state != VideoProgress.ABORTED

    def discard_created_frames():
        try:
            s3_repo.delete_frame_files(created_frame_uuids)
        finally:
            event_loop.run_until_complete(
                frame_repo.delete_by_ids(created_frame_ids)
            )
            event_loop.run_until_complete(frame_repo.commit())

    batches = batch_generator(
        frame_generator(video_url, frame_interval, "jpg"),
        batch_size,
    )
    try:
        for batch in batches:
            if not should_continue():
                discard_created_frames()
                return

            orm_frames = [
                Frame(
                    video_key=video_key,
                    timestamp=item["timestamp"],
                    index=item["index"],
                )
                for item in batch
            ]

            try:
                frame_repo.add_all(orm_frames)
                event_loop.run_until_complete(frame_repo.commit())
            except Exception as err:
                event_loop.run_until_complete(frame_repo.rollback())
                raise RuntimeError("Failed to insert Frame data to DB") from err

            frame_ids = [frame.key for frame in orm_frames]
            frame_uuids = [str(frame.uuid) for frame in orm_frames]
            created_frame_ids.extend(frame_ids)
            created_frame_uuids.extend(frame_uuids)

            if not should_continue():
                discard_created_frames()
                return

            for item, frame_uuid in zip(batch, frame_uuids):
                s3_repo.upload(item["frame"], f"temp/{frame_uuid}.jpg")

            if not should_continue():
                discard_created_frames()
                return

            redis_repo.add_extracted(redis_key, len(batch))
            frame_embedding.delay(frame_uuids, video_key, frame_ids)

        transitioned = event_loop.run_until_complete(
            video_repo.set_state_if_not_aborted(
                video_key, VideoProgress.FRAME_COMPLETE
            )
        )
        event_loop.run_until_complete(video_repo.commit())
        if not transitioned or not redis_repo.set_state_if_not_aborted(
            redis_key, VideoProgress.FRAME_COMPLETE
        ):
            discard_created_frames()
    except Exception:
        if not should_continue():
            discard_created_frames()
            return
        raise
