import asyncio
import os
from typing import List

import numpy as np
from qdrant_client.http.exceptions import UnexpectedResponse

from ai.models.clip import (
    load_clip_vision_model,
    load_clip_processor,
    get_device,
)
from infra.db.connections import AsyncMariaDBConnection
from infra.db.repositories import AsyncFrameRepository, AsyncVideoRepository
from infra.qdrant.connections import AsyncQdrantConnection
from infra.qdrant.repositories import AsyncQdrantRepository
from infra.s3.connections import S3Connection
from infra.s3.repositories import S3Repositories
from infra.redis.connections import RedisConnection
from infra.redis.repositories import VideoRedisRepository
from backend.ai.models.encoder import image_embedding, image_projection
from schema.frame import FrameMetadata, QdrantPoint
from utils.exceptions import CollectionNotFoundException
from utils.frames import bytes_to_numpy
from utils.enums import VideoProgress
from workers.worker import celery_app

MAX_RETRIES = 3


@celery_app.task(queue="image_embedding")
def frame_embedding(s3_keys: List[str], video_key: int, frame_ids: List[int]):
    # initialization
    s3_client = S3Connection.get_client()
    s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])
    redis_client = RedisConnection.get_client()
    redis_repo = VideoRedisRepository(redis_client)
    qdrant_client = AsyncQdrantConnection.get_client()
    qdrant_repo = AsyncQdrantRepository(qdrant_client, os.environ["FRAME_COLLECTION"])
    async_session = AsyncMariaDBConnection.get_session()
    video_repo = AsyncVideoRepository(async_session)
    frame_repo = AsyncFrameRepository(async_session)
    event_loop = asyncio.get_event_loop()

    device = get_device()
    model = load_clip_vision_model()
    model.to(device)
    processor = load_clip_processor()

    video = event_loop.run_until_complete(video_repo.find_by_id(video_key))

    # preprocess
    bytes_io = s3_repo.download_batch_fileobj(s3_keys)
    frame_list = [bytes_to_numpy(b) for b in bytes_io]
    imgs = np.stack(frame_list)

    # inference
    embeds = image_embedding(model, processor, imgs, device)
    embeds = image_projection(model, embeds)

    # makes frame metadata
    orm_frames = event_loop.run_until_complete(frame_repo.search_by_ids(frame_ids))
    frames_meta = [
        FrameMetadata(video_key, frame.key, frame.timestamp, frame.index)
        for frame in orm_frames
    ]

    # uploads to Qdrant
    points = []
    for id, tensor_embed, meta in zip(frame_ids, embeds, frames_meta):
        embed = tensor_embed.detach().cpu().numpy().tolist()
        points.append(QdrantPoint(id, embed, meta.to_dict()).to_dict())
    collection_name = os.environ["FRAME_COLLECTION"]

    try:
        event_loop.run_until_complete(qdrant_repo.upsert_data(points))
        redis_repo.add_processed(video.uuid, len(embeds))
    except UnexpectedResponse as e:
        code = e.status_code
        if code == 404:
            raise CollectionNotFoundException(
                f'Unidentified collection "{collection_name}"'
            )

    # update progress to DB
    video_state = redis_repo.get_video_state(video_key)
    if video_state == VideoProgress.FRAME_COMPLETE:
        task_count = redis_repo.get_extracted(video_key)
        processed_count = redis_repo.get_processed(video_key)
        if task_count == processed_count:
            try:
                redis_repo.set_state(video_key, VideoProgress.COMPLETE)
                event_loop.run_until_complete(
                    video_repo.set_state(video_key, VideoProgress.COMPLETE)
                )
                event_loop.run_until_complete(video_repo.commit())
            except:
                event_loop.run_until_complete(video_repo.rollback())
