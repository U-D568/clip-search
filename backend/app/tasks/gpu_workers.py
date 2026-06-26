from multiprocessing.shared_memory import SharedMemory
import os
from typing import List

import numpy as np
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.enums import FrameState
from app.schema.dto import QdrantPoint, FrameMeta
from app.db.connections import MariaDBConnection, QdrantConnection
from app.db.repositories import (
    FrameRepository,
    QdrantRepository,
    FrameProgressRepository,
    VideoRepository
)
from app.encoders.encoder import (
    image_embedding,
    image_projection,
    text_encoding,
    text_projection,
)
from app.utils.models import (
    load_clip_vision_model,
    load_clip_processor,
    get_device,
    load_clip_text_model,
)
from app.s3.connections import S3Connection
from app.s3.repositories import S3Repositories
from app.redis.connections import RedisConnection
from app.redis.repositories import RedisRepository
from app.tasks.worker import celery_app
from app.exceptions import CollectionNotFoundException
from app.utils.frames import bytes_to_numpy
from app.enums import VideoProgress

MAX_RETRIES = 3


@celery_app.task(queue="embedding_queue")
def frame_embedding(s3_keys: List[str], video_id: int, frame_ids: List[int]):
    # clients
    s3_client = S3Connection.get_client()
    redis_client = RedisConnection.get_client()
    qdrant_client = QdrantConnection.get_client()

    # repositories
    s3_repo = S3Repositories(s3_client, os.environ["CLIP_BUCKET_NAME"])
    redis_repo = RedisRepository(redis_client)
    qdrant_repo = QdrantRepository(qdrant_client, os.environ["FRAME_COLLECTION"])

    # data prepraration
    bytes_io = s3_repo.download_batch_fileobj(s3_keys)
    frame_list = [bytes_to_numpy(b) for b in bytes_io]
    imgs = np.stack(frame_list)

    device = get_device()
    model = load_clip_vision_model()
    model.to(device)
    processor = load_clip_processor()
    embeds = image_embedding(model, processor, imgs, device)
    embeds = image_projection(model, embeds)

    # retrieves frame metadata
    with MariaDBConnection.get_session() as session:
        # DB repositories
        frame_repo = FrameRepository(session)
        video_repo = VideoRepository(session)

        frames = frame_repo.search_by_ids(frame_ids)
        frames_meta = [
            FrameMeta(video_id, frame.key, frame.timestamp, frame.index)
            for frame in frames
        ]

        # uploads to Qdrant DB
        points = []
        for id, tensor_embed, meta in zip(frame_ids, embeds, frames_meta):
            list_embed = tensor_embed.detach().cpu().numpy().tolist()
            points.append(QdrantPoint(id, list_embed, meta.to_dict()).to_dict())
        collection_name = os.environ["FRAME_COLLECTION"]

        try:
            qdrant_repo.upsert_data(collection_name, points)
            redis_repo.add_video_processed(video_id, len(embeds))
        except UnexpectedResponse as e:
            code = e.status_code
            if code == 404:
                raise CollectionNotFoundException(
                    f'Unidentified collection "{collection_name}"'
                )

        # update progress to DB
        video_state = redis_repo.get_video_state(video_id)
        if video_state == VideoProgress.FRAME_COMPLETE:
            task_count = redis_repo.get_video_tasks(video_id)
            processed_count = redis_repo.get_video_processed(video_id)

            if task_count == processed_count:
                redis_repo.set_video_state(video_id, VideoProgress.COMPLETE)
                video_repo.set_state(video_id, VideoProgress.COMPLETE)
                video_repo.commit()


@celery_app.task(queue="text_queue")
def text_embedding(text_query: str, video_id: int, topk=5) -> List[int]:
    # initaliation
    device = get_device()
    model = load_clip_text_model()
    model.to(device)
    processor = load_clip_processor()

    # text embedding and projection
    text_embeds = text_encoding(model, processor, text_query, device)
    text_embeds = text_projection(model, text_embeds)
    text_embeds = text_embeds.detach().cpu().tolist()

    qdrant_client = QdrantConnection.get_client()
    collection_name = os.environ["FRAME_COLLECTION"]
    qdrant_repo = QdrantRepository(qdrant_client, collection_name)
    ids = qdrant_repo.query_image_in_video(collection_name, text_embeds, video_id, topk)

    return ids
