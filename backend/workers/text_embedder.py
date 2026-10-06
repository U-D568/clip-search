import asyncio
import os
from typing import List

from ai.models.clip import load_clip_processor, get_device, load_clip_text_model
from infra.db.connections import AsyncMariaDBConnection
from infra.db.repositories import AsyncVideoRepository
from infra.redis.connections import RedisConnection
from infra.redis.repositories import QueryRedisRepository
from infra.qdrant.repositories import AsyncQdrantRepository
from ai.models.encoder import text_encoding, text_projection
from workers.worker import celery_app
from utils.enums import QueryProgress


@celery_app.task(queue="text_queue")
def text_embedding(text_query: str, task_uuid: str, topk=5) -> List[int]:
    # init
    redis_client = RedisConnection.get_client()
    redis_repo = QueryRedisRepository(redis_client)
    db_session = AsyncMariaDBConnection.get_session()
    video_repo = AsyncVideoRepository(db_session)
    event_loop = asyncio.get_event_loop()

    redis_repo.publish(task_uuid, QueryProgress.IN_PROGRESS)
    query_state = redis_repo.get_query(task_uuid)

    video = event_loop.run_until_complete(
        video_repo.find_by_id(query_state.video_key)
    )
    if video is None:
        raise LookupError(f"Video with key {query_state.video_key} was not found")

    # load model
    device = get_device()
    model = load_clip_text_model()
    model.to(device)
    processor = load_clip_processor()

    # text embedding and projection
    text_embeds = text_encoding(model, processor, text_query, device)
    text_embeds = text_projection(model, text_embeds)
    text_embeds = text_embeds.detach().cpu().tolist()

    # vector search
    qdrant_client = AsyncQdrantRepository.get_client()
    collection_name = os.environ["FRAME_COLLECTION"]
    qdrant_repo = AsyncQdrantRepository(qdrant_client, collection_name)
    timestamps = qdrant_repo.search(
        collection_name, text_embeds, video.key, topk
    )

    return timestamps
