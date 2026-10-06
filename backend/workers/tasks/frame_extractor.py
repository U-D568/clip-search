import asyncio
import os
from typing import List

from infra.db.connections import AsyncMariaDBConnection
from infra.db.models import Frame
from infra.db.repositories import AsyncFrameRepository, AsyncVideoRepository
from infra.redis.connections import RedisConnection
from infra.redis.repositories import VideoRedisRepository
from infra.s3.connections import S3Connection
from infra.s3.repositories import S3Repositories
from utils.enums import VideoProgress
from utils.frames import batch_generator, frame_generator
from workers.tasks.image_embedder import frame_embedding
from workers.worker import celery_app


class FrameExtractorWorker:
    def __init__(self) -> None:
        self.event_loop = asyncio.get_event_loop()

        s3_client = S3Connection.get_client()
        self.s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])

        redis_client = RedisConnection.get_client()
        self.redis_repo = VideoRedisRepository(redis_client)

        async_session = AsyncMariaDBConnection.get_session()
        self.frame_repo = AsyncFrameRepository(async_session)
        self.video_repo = AsyncVideoRepository(async_session)

    def run(
        self,
        video_key: int,
        frame_interval: float = 1.0,
        batch_size: int = 32,
    ) -> None:
        video = self.event_loop.run_until_complete(
            self.video_repo.find_by_id(video_key)
        )
        if video is None or video.state == VideoProgress.ABORTED:
            return

        # Set the video state to IN_PROGRESS if it is not already aborted
        is_updated = self.event_loop.run_until_complete(
            self.video_repo.set_state_if_not_aborted(
                video_key, VideoProgress.IN_PROGRESS
            )
        )
        if not is_updated:
            self.event_loop.run_until_complete(self.video_repo.rollback())
            return
        self.event_loop.run_until_complete(self.video_repo.commit())

        # get video url and initialize redis progress
        video_url = self.s3_repo.get_url(video.file_path)
        redis_key = str(video.key)
        self.redis_repo.init_progress(redis_key)
        self.redis_repo.publish_state(redis_key, VideoProgress.IN_PROGRESS)

        created_frame_ids: List[int] = []
        created_frame_uuids: List[str] = []

        batches = batch_generator(
            frame_generator(video_url, frame_interval, "jpg"),
            batch_size,
        )
        try:
            for batch in batches:
                if not self._is_aborted(redis_key):
                    self._discard_created_frames(created_frame_ids, created_frame_uuids)
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
                    self.frame_repo.add_all(orm_frames)
                    self.event_loop.run_until_complete(self.frame_repo.commit())
                except Exception as error:
                    self.event_loop.run_until_complete(self.frame_repo.rollback())
                    raise RuntimeError("Failed to insert Frame data to DB") from error

                frame_ids = [frame.key for frame in orm_frames]
                frame_uuids = [str(frame.uuid) for frame in orm_frames]
                created_frame_ids.extend(frame_ids)
                created_frame_uuids.extend(frame_uuids)

                if not self._is_aborted(redis_key):
                    self._discard_created_frames(created_frame_ids, created_frame_uuids)
                    return

                self.redis_repo.add_extracted(
                    redis_key, len(batch)
                )  # update the extracted count in Redis
                for item, frame_uuid in zip(batch, frame_uuids):  # upload frames to S3
                    self.s3_repo.upload(item["frame"], f"temp/{frame_uuid}.jpg")

                frame_embedding.delay(video_key, frame_ids, frame_uuids)

            is_updated = self.event_loop.run_until_complete(
                self.video_repo.set_state_if_not_aborted(
                    video_key, VideoProgress.FRAME_COMPLETE
                )
            )
            if not is_updated:
                self._discard_created_frames(created_frame_ids, created_frame_uuids)
                return
            self.event_loop.run_until_complete(self.video_repo.commit())

            is_updated = self.redis_repo.set_state_if_not_aborted(redis_key, VideoProgress.FRAME_COMPLETE)
            if not is_updated:
                self._discard_created_frames(created_frame_ids, created_frame_uuids)
                return
        except Exception:
            if not self._is_aborted(redis_key):
                self._discard_created_frames(created_frame_ids, created_frame_uuids)
                return
            raise

    def _is_aborted(self, key: str) -> bool:
        state = self.redis_repo.get_state(key)
        return state is not None and state != VideoProgress.ABORTED

    def _discard_created_frames(
        self,
        frame_ids: List[int],
        frame_uuids: List[str],
    ) -> None:
        try:
            self.s3_repo.delete_frame_files(frame_uuids)
        finally:
            self.event_loop.run_until_complete(self.frame_repo.delete_by_ids(frame_ids))
            self.event_loop.run_until_complete(self.frame_repo.commit())


@celery_app.task(queue="extraction_queue", name="frame_extractor")
def frame_extractor(
    video_key: int,
    frame_interval: float = 1.0,
    batch_size: int = 32,
) -> None:
    FrameExtractorWorker().run(video_key, frame_interval, batch_size)
