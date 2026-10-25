import asyncio
import os
from typing import List, Optional

import numpy as np
from qdrant_client.http.exceptions import UnexpectedResponse

from ai.models.clip import get_device, load_clip_processor, load_clip_vision_model
from ai.models.encoder import image_embedding, image_projection
from infra.db.connections import AsyncMariaDBConnection
from infra.db.models import Video
from infra.db.repositories import AsyncFrameRepository, AsyncVideoRepository
from infra.qdrant.connections import AsyncQdrantConnection
from infra.qdrant.repositories import AsyncQdrantRepository
from infra.redis.connections import RedisConnection
from infra.redis.repositories import AsyncRedisVideoRepository
from infra.s3.connections import S3Connection
from infra.s3.repositories import S3Repositories
from schema.frame import PointMetadata, QdrantPoint
from utils.enums import VideoProgress
from utils.exceptions import CollectionNotFoundException
from utils.frames import bytes_to_numpy
from workers.worker import celery_app


class FrameEmbeddingWorker:
    def __init__(self) -> None:
        s3_client = S3Connection.get_client()
        self.s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])

        redis_client = RedisConnection.get_client()
        self.redis_repo = AsyncRedisVideoRepository(redis_client)

        qdrant_client = AsyncQdrantConnection.get_client()
        self.qdrant_repo = AsyncQdrantRepository(
            qdrant_client, os.environ["FRAME_COLLECTION"]
        )

        async_session = AsyncMariaDBConnection.get_session()
        self.video_repo = AsyncVideoRepository(async_session)
        self.frame_repo = AsyncFrameRepository(async_session)
        self.event_loop = asyncio.get_event_loop()

        self.device = get_device()

    def run(
        self,
        video_key: int,
        frame_ids: List[int],
        frame_uuids: List[str]
    ) -> None:
        video: Optional[Video] = None
        video = self.event_loop.run_until_complete(
            self.video_repo.find_by_id(video_key)
        )
        if video is None or video.state == VideoProgress.ABORTED:
            self._discard_embedded_frames(frame_ids, frame_uuids)
            return

        # model initialization
        model = load_clip_vision_model()
        model.to(self.device)
        processor = load_clip_processor()

        frame_files = self.s3_repo.download_frame_files(frame_uuids)
        images = np.stack([bytes_to_numpy(frame) for frame in frame_files])

        embeds = image_embedding(model, processor, images, self.device)
        embeds = image_projection(model, embeds)

        # get frame metadata from the database
        orm_frames = self.event_loop.run_until_complete(
            self.frame_repo.search_by_ids(frame_ids)
        )

        if not orm_frames:  # if frames are not found in the database, discard the batch
            self._discard_embedded_frames(frame_ids, frame_uuids)
            return

        # DB query order is not guaranteed, so match frames to embeddings by id
        frames_by_id = {frame.key: frame for frame in orm_frames}

        points = []
        for frame_id, tensor_embed in zip(frame_ids, embeds):
            frame = frames_by_id.get(frame_id)
            if frame is None:
                continue

            metadata = PointMetadata(
                video_key=video_key,
                frame_key=frame.key,
                timestamp=frame.timestamp,
                index=frame.index,
            )
            embed = tensor_embed.detach().cpu().numpy().tolist()
            point = QdrantPoint(id=frame_id, vector=embed, payload=metadata)
            points.append(point.model_dump())

        # saves embeddings to vector database
        self.event_loop.run_until_complete(self.qdrant_repo.upsert_data(points))

        # add updated count of frames to redis
        state = self.event_loop.run_until_complete(
            self.redis_repo.add_processed, len(points)
        )

        if state == VideoProgress.COMPLETE:
            is_updated = self.event_loop.run_until_complete(
                self.video_repo.set_state_if_not_aborted(
                    video_key, VideoProgress.COMPLETE
                )
            )
            self.event_loop.run_until_complete(self.video_repo.commit())
            if is_updated:
                redis_key = str(video_key)
                self.event_loop.run_until_complete(
                    self.redis_repo.publish_state(redis_key, VideoProgress.COMPLETE)
                )
        elif state == VideoProgress.ABORTED or state == VideoProgress.ERROR:
            self._discard_embedded_frames(frame_ids, frame_uuids)

    def _discard_embedded_frames(
        self, frame_ids: List[int], frame_uuids: List[str]
    ) -> None:
        self.event_loop.run_until_complete(self.qdrant_repo.delete_by_ids(frame_ids))
        self.s3_repo.delete_frame_files(frame_uuids)
        self.event_loop.run_until_complete(self.frame_repo.delete_by_ids(frame_ids))
        self.event_loop.run_until_complete(self.frame_repo.commit())


@celery_app.task(queue="embedding_queue", name="frame_embedding")
def frame_embedding(
    video_key: int, frame_ids: List[int], frame_uuids: List[str]
) -> None:
    FrameEmbeddingWorker().run(video_key, frame_ids, frame_uuids)
