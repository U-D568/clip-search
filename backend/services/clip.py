from typing import List

from celery.result import AsyncResult
from starlette.concurrency import run_in_threadpool
import numpy as np
import torch

from ai.models.clip import get_device
from backend.ai.models.encoder import (
    text_encoding,
    text_projection,
    image_embedding,
    image_projection,
)
from ai.utils.ops import cosine_similarity
from infra.db.models import Video, User
from workers.text_embedder import text_embedding
from infra.redis.connections import RedisConnection
from infra.redis.repositories import QueryRedisRepository
from utils.exceptions import AuthenticationException


class CLIPService:
    def __init__(self, redis_repo: QueryRedisRepository):
        self.redis_repo = redis_repo

    async def query_frame(self, query_text: str, video: Video, user: User):
        # start embedding task
        task = text_embedding.delay(query_text, video.key)

        # add to redis
        self.redis_repo.register_task(task.id, user.uuid)
        return task.id

    async def get_query_result(self, task_id: str, user: User) -> List[str]:
        # validate task ownership
        owner_uuid = self.redis_repo.get_task_owner(task_id)
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
