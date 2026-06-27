from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.db.models import Video, User
from app.db.repositories import AsyncVideoRepository
from app.tasks.cpu_workers import frame_extractor
from app.exceptions import (
    ResourceNotFoundException,
    DuplicatedVideoTitleException,
)
from app.s3.repositories import S3Repositories
from app.enums import VideoProgress


class VideoService:
    def __init__(self, video_repo: AsyncVideoRepository, s3_repo: S3Repositories):
        self.video_repo = video_repo
        self.s3_repo = s3_repo

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
                state=VideoProgress.QUEUED
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

        frame_extractor.delay(s3_key, new_video.key)

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
