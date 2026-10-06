import asyncio
import os
from typing import List

from ai.models.clip import get_device, load_clip_processor, load_clip_text_model
from ai.models.encoder import text_encoding, text_projection
from infra.db.connections import AsyncMariaDBConnection
from infra.db.repositories import AsyncVideoRepository
from infra.qdrant.connections import AsyncQdrantConnection
from infra.qdrant.repositories import AsyncQdrantRepository
from infra.redis.connections import RedisConnection
from infra.redis.repositories import QueryRedisRepository
from utils.enums import QueryProgress
from workers.worker import celery_app


class TextEmbeddingWorker:
    def __init__(self) -> None:
        self.event_loop = asyncio.get_event_loop()
        self.redis_repo = QueryRedisRepository(RedisConnection.get_client())

        async_session = AsyncMariaDBConnection.get_session()
        self.video_repo = AsyncVideoRepository(async_session)

        collection_name = os.environ["FRAME_COLLECTION"]
        self.qdrant_repo = AsyncQdrantRepository(
            AsyncQdrantConnection.get_client(), collection_name
        )
        self.device = get_device()

    def run(self, text_query: str, task_uuid: str, topk: int = 5) -> List[int]:
        self._set_state(task_uuid, QueryProgress.IN_PROGRESS)

        try:
            if topk <= 0:
                raise ValueError("topk must be greater than zero")

            query_state = self.redis_repo.get_query(task_uuid)
            video = self.event_loop.run_until_complete(
                self.video_repo.find_by_id(query_state.video_key)
            )
            if video is None:
                raise LookupError(
                    f"Video with key {query_state.video_key} was not found"
                )

            model = load_clip_text_model()
            model.to(self.device)
            processor = load_clip_processor()

            text_embeds = text_encoding(model, processor, text_query, self.device)
            text_embeds = text_projection(model, text_embeds)
            query_vector = text_embeds[0].detach().cpu().tolist()

            response = self.event_loop.run_until_complete(
                self.qdrant_repo.query_video(query_vector, video.key, topk)
            )
            frame_ids = [int(point.id) for point in response.points]

            self.redis_repo.set_ids(task_uuid, frame_ids)
            self._set_state(task_uuid, QueryProgress.COMPLETE)
            return frame_ids
        except Exception as error:
            try:
                self._set_state(task_uuid, QueryProgress.ERROR)
            except Exception as state_error:
                raise state_error from error
            raise

    def _set_state(self, task_uuid: str, state: QueryProgress) -> None:
        self.redis_repo.set_state(task_uuid, state)
        self.redis_repo.publish(task_uuid, state)


@celery_app.task(queue="text_queue", name="text_embedding")
def text_embedding(
    text_query: str,
    task_uuid: str,
    topk: int = 5,
) -> List[int]:
    return TextEmbeddingWorker().run(text_query, task_uuid, topk)
