import os
from typing import List

from celery.result import AsyncResult
from starlette.concurrency import run_in_threadpool
from qdrant_client.models import Filter, FieldCondition, MatchValue
import numpy as np
import torch

from app.utils.models import load_clip_model, load_clip_processor, get_device
from app.encoders.encoder import (
    text_encoding,
    text_projection,
    image_embedding,
    image_projection,
)
from app.utils.ops import cosine_similarity
from app.db.repositories import QdrantRepository, AsyncFrameRepository
from app.db.models import Video, User
from app.schema.dto import QdrantPoint
from app.tasks.gpu_workers import text_embedding
from app.redis.connections import RedisConnection
from app.redis.repositories import RedisRepository
from app.exceptions import AuthenticationException


class CLIPService:
    def __init__(self):
        pass

    def query_frame(self, query_text: str, video: Video, user: User):
        # init redis repo
        redis_client = RedisConnection.get_client()
        redis_repo = RedisRepository(redis_client)

        # start embedding task
        task = text_embedding.delay(query_text, video.key)

        # add to redis
        redis_repo.register_task(task.id, user.uuid)
        return task.id

    async def get_query_result(self, task_id: str, user: User) -> List[str]:
        # init redis repo
        redis_client = RedisConnection.get_client()
        redis_repo = RedisRepository(redis_client)

        # validate task ownership
        owner_uuid = redis_repo.get_task_owner(task_id)
        if owner_uuid != user.uuid:
            raise AuthenticationException()
        
        # retrieve the result of text embedding task
        task = AsyncResult(task_id)
        timestamps = await run_in_threadpool(task.get)

        return timestamps


class CLIPServiceLegacy:
    def __init__(self):
        self._device = get_device()

    def text_embedding(self, model, processor, text: List[str]) -> torch.Tensor:
        text_embeds = text_encoding(model, processor, text, self._device)
        text_embeds = text_projection(model, text_embeds)

        return text_embeds

    def image_embedding(
        self, model, processor, images: List[np.ndarray]
    ) -> torch.Tensor:
        image_embeds = image_embedding(model, processor, images, self._device)
        image_embeds = image_projection(model, image_embeds)

        return image_embeds

    def query_image(
        self, text_embeds: torch.Tensor, image_embeds: torch.Tensor, topk=5
    ) -> List[int]:
        similarity = cosine_similarity(text_embeds, image_embeds)
        indices = similarity.topk(k=topk, dim=-1).indices.numpy().tolist()[0]

        return indices


class QdrantService:
    def search_image(
        self,
        qdrant_repo: QdrantRepository,
        collection_name: str,
        image_embed: List[float],
        video_id: int,
    ):
        video_key = os.environ["VIDEO_KEY"]
        filter = Filter(must=FieldCondition(key=video_key, match=MatchValue(video_id)))
        return qdrant_repo.search(
            collection_name, query_vector=image_embed, filter=filter
        )

    def upload_frames(
        self, qdrant_repo: QdrantRepository, collection_name, points: List[QdrantPoint]
    ):
        serialized = list(map(lambda obj: obj.to_dict()), points)
        return qdrant_repo.upsert_data(collection_name, serialized)

    def delete_video(
        self, qdrant_repo: QdrantRepository, collection_name: str, video_id
    ):
        video_key = os.environ["VIDEO_KEY"]
        filter = Filter(must=FieldCondition(key=video_key, match=MatchValue(video_id)))
        qdrant_repo.delete(collection_name, filter)
