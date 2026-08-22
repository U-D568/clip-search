from typing import List, AsyncGenerator

from starlette.concurrency import run_in_threadpool
import numpy as np
import torch

from ai.models.clip import get_device
from ai.models.encoder import (
    text_encoding,
    text_projection,
    image_embedding,
    image_projection,
)
from ai.utils.ops import cosine_similarity
from workers.text_embedder import text_embedding
from infra.db.repositories import AsyncVideoRepository, AsyncUserRepository
from infra.redis.repositories import AsyncQueryReidsRepository
from utils.exceptions import AuthenticationException
from utils.enums import QueryProgress


class CLIPService:
    def __init__(
        self,
        user_repo: AsyncUserRepository,
        video_repo: AsyncVideoRepository,
        query_repo: AsyncQueryReidsRepository,
    ):
        self.user_repo = user_repo
        self.video_repo = video_repo
        self.query_repo = query_repo

    async def query_frame(self, video_uuid: str, query_text: str, username: str) -> str:
        user = await self.user_repo.get_by_username(username)
        video = await self.video_repo.find_by_uuid(video_uuid, user.key)

        # register task info to redis
        task_id = await self.query_repo.register_query(video.uuid, user.uuid)

        # start embedding task
        text_embedding.delay(query_text, video.key)

        return task_id

    async def get_query_result(
        self, task_uuid: str, username: str
    ) -> AsyncGenerator[List[int], None]:
        user = await self.user_repo.get_by_username(username)
        query = await self.query_repo.get_query(task_uuid)
        if query.owner != user.uuid:
            raise AuthenticationException()

        if query.state == QueryProgress.COMPLETE:
            ids = await self.query_repo.get_ids(task_uuid)
            yield ids
            return

        async for state in self.query_repo.subscribe():
            if state == QueryProgress.COMPLETE:
                break

        return await self.query_repo.get_ids(task_uuid)


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
