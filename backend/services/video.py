from datetime import datetime
from pathlib import Path
from typing import List, AsyncGenerator

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from infra.db.models import Video, User
from infra.db.repositories import AsyncVideoRepository
from infra.qdrant.repositories import AsyncQdrantRepository
from infra.s3.repositories import S3Repositories
from workers.tasks.frame_extractor import frame_extractor
from utils.exceptions import (
    ResourceNotFoundException,
    DuplicatedVideoTitleException,
    InvalidCredentialsException,
)
from utils.enums import VideoProgress
from infra.redis.repositories import AsyncRedisVideoRepository


class VideoService:
    def __init__(
        self,
        video_repo: AsyncVideoRepository,
        s3_repo: S3Repositories,
        qdrant_repo: AsyncQdrantRepository,
        redis_repo: AsyncRedisVideoRepository,
    ):
        self.video_repo = video_repo
        self.s3_repo = s3_repo
        self.qdrant_repo = qdrant_repo
        self.redis_repo = redis_repo

    async def register_video(self, file: UploadFile, title: str, user: User):
        # save to s3 storage
        ext = Path(file.filename).suffix
        username = user.username
        s3_key = f"{username}/{title}{ext}"

        try:
            # update data to database
            new_video = Video(
                file_path=s3_key,
                title=title,
                uploaded_time=datetime.now(),
                owner=user.key,
                state=VideoProgress.QUEUED,
            )
            self.video_repo.add(new_video)

            await self.video_repo.commit()

            # upload to storage
            self.s3_repo.upload(file.file, s3_key)

        except IntegrityError as err:
            await self.video_repo.rollback()
            raise DuplicatedVideoTitleException(f"{title} is already exist")
        except Exception as err:
            await self.video_repo.rollback()
            raise Exception(err)

        frame_extractor.delay(new_video.key)

    async def find_video(self, video_title: str, user: User) -> Video:
        video = await self.video_repo.find_by_title(video_title, user.key)
        if video is None:
            raise ResourceNotFoundException()
        return video

    async def find_video_by_uuid(self, video_uuid: str, user: User) -> Video:
        video = await self.video_repo.find_by_uuid(video_uuid, user.key)
        if video is None:
            raise ResourceNotFoundException()
        return video

    async def validate_ownership(self, video: Video, user: User) -> bool:
        video = await self.video_repo.find_by_id(video.key)
        if video.owner == user.key:
            return True
        else:
            return False

    async def get_all_videos(self, user: User) -> List[Video]:
        return await self.video_repo.find_all_by_user_id(user.key)

    async def remove_video(self, video: Video, user: User):
        if video.owner != user.key:
            raise InvalidCredentialsException()

        try:
            redis_key = str(video.key)
            await self.redis_repo.set_state(redis_key, VideoProgress.ABORTED)
            await self.video_repo.set_state(video.key, VideoProgress.ABORTED)
            await self.video_repo.commit()
            await self.redis_repo.publish_state(redis_key, VideoProgress.ABORTED)

            frame_uuids = await self.video_repo.find_frame_uuids_by_video_id(
                video.key
            )
            await self.qdrant_repo.delete_by_key(video.key)
            self.s3_repo.delete_video_files(video.file_path, frame_uuids)
            await self.video_repo.delete(video)
            await self.video_repo.commit()
        except Exception:
            await self.video_repo.rollback()
            raise

    async def get_video_state(self, video: Video) -> AsyncGenerator[VideoProgress, None]:
        if video.state == VideoProgress.COMPLETE:
            yield video.state
            return

        redis_key = str(video.key)
        generator = self.redis_repo.subscribe(redis_key)
        async for state in generator:
            yield state
        await self.redis_repo.delete_progress(redis_key)
