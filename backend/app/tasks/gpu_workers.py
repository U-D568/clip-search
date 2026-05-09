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
)
from app.encoders.encoder import image_embedding, image_projection, text_encoding, text_projection
from app.utils.models import load_clip_vision_model, load_clip_processor, get_device, load_clip_text_model
from app.tasks.worker import celery_app
from app.exceptions import CollectionNotFoundException

MAX_RETRIES = 3


@celery_app.task(queue="embedding_queue")
def frame_embedding(
    shm_name: str, shape: List[int], dtype: str, video_id: int, frame_ids: List[int]
):
    shared_memory = SharedMemory(shm_name)
    dtype = np.dtype(dtype)
    imgs = np.ndarray(shape=shape, dtype=dtype, buffer=shared_memory.buf)

    device = get_device()
    model = load_clip_vision_model()
    model.to(device)
    processor = load_clip_processor()
    embeds = image_embedding(model, processor, imgs, device)
    embeds = image_projection(model, embeds)

    # retrieves frame metadata
    with MariaDBConnection.get_session() as session:
        # Qdrant client
        qdrant_client = QdrantConnection.get_client()

        # DB repositories
        frame_repo = FrameRepository(session)
        frame_progress_repo = FrameProgressRepository(session)

        # 프로그래스 업데이트 할 repository 생성
        qdrant_repo = QdrantRepository(qdrant_client)
        frames = frame_repo.search_by_ids(frame_ids)

        frame_meta_list = [
            FrameMeta(video_id, frame.key, frame.timestamp, frame.index)
            for frame in frames
        ]

        # uploads to Qdrant DB
        points = []
        for id, tensor_embed, meta in zip(frame_ids, embeds, frame_meta_list):
            list_embed = tensor_embed.detach().cpu().numpy().tolist()
            points.append(QdrantPoint(id, list_embed, meta.to_dict()).to_dict())
        collection_name = os.environ["FRAME_COLLECTION"]
        try:
            qdrant_repo.upsert_data(collection_name, points)
        except UnexpectedResponse as e:
            code = e.status_code
            if code == 404:
                raise CollectionNotFoundException(
                    f'Unidentified collection "{collection_name}"'
                )

        # update progress to DB
        progresses = frame_progress_repo.get_by_frame_ids(frame_ids)
        for progress in progresses:
            progress.status = FrameState.DONE
        frame_progress_repo.commit()

    # frees shared memory
    shared_memory.unlink()
    shared_memory.close()

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
    qdrant_repo = QdrantRepository(qdrant_client)
    collection_name = os.environ["FRAME_COLLECTION"]
    ids = qdrant_repo.query_image_in_video(collection_name, text_embeds, video_id, topk)

    return ids