from typing import List, AsyncGenerator

from infra.db.repositories import (
    AsyncVideoRepository,
    AsyncUserRepository,
    AsyncFrameRepository,
)
from infra.redis.repositories import AsyncRedisQueryRepository
from infra.s3.repositories import S3Repositories
from schema.frame import FrameSearchResult
from utils.enums import QueryProgress
from utils.exceptions import ResourceNotFoundException
from workers.tasks.text_embedder import text_embedding


class CLIPService:
    def __init__(
        self,
        user_repo: AsyncUserRepository,
        video_repo: AsyncVideoRepository,
        frame_repo: AsyncFrameRepository,
        query_repo: AsyncRedisQueryRepository,
        s3_repo: S3Repositories,
    ):
        self.user_repo = user_repo
        self.video_repo = video_repo
        self.frame_repo = frame_repo
        self.query_repo = query_repo
        self.s3_repo = s3_repo

    async def query_frame(
        self, video_uuid: str, query_text: str, username: str
    ) -> AsyncGenerator[List[FrameSearchResult], None]:
        user = await self.user_repo.get_by_username(username)
        video = await self.video_repo.find_by_uuid(video_uuid, user.key)
        if video is None:
            raise ResourceNotFoundException()

        # register task info to redis
        task_uuid = await self.query_repo.register_query(video.key, user.key)

        # start embedding task
        text_embedding.delay(query_text, task_uuid)

        async for state in self.query_repo.subscribe(task_uuid):
            if state == QueryProgress.COMPLETE:
                frame_ids = await self.query_repo.get_ids(task_uuid)
                yield await self._get_frames(frame_ids)
                break
            if state == QueryProgress.ERROR:
                raise RuntimeError(f"Text embedding query {task_uuid} failed")

    async def _get_frames(self, frame_ids: List[int]) -> List[FrameSearchResult]:
        frames = await self.frame_repo.search_by_ids(frame_ids)
        frames_by_id = {frame.key: frame for frame in frames}

        # keep the similarity order returned by the vector search
        return [
            FrameSearchResult(
                frame_id=frame.key,
                timestamp=frame.timestamp,
                index=frame.index,
                thumbnail_url=self.s3_repo.get_frame_url(frame.uuid),
            )
            for frame_id in frame_ids
            if (frame := frames_by_id.get(frame_id)) is not None
        ]
