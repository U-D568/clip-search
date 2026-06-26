from datetime import datetime
import os
from pathlib import Path
import uuid

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.db.models import Video, User
from app.db.repositories import AsyncVideoRepository
from app.tasks.cpu_workers import frame_extractor
from app.utils.file import save_video_to_local
from app.exceptions import (
    FileWriteException,
    DBWriteException,
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

        # test code
        # frame_extractor.delay(str(s3_key), new_video.key)
        frame_extractor.delay(str(s3_key), 8)

    async def find_video(self, video_title: str, user_id: int) -> Video:
        video = await self.video_repo.find_by_title(video_title, user_id)
        if video is None:
            raise ResourceNotFoundException()
        return video

    async def validate_ownership(self, video_id: int, user_id: int) -> bool:
        video = await self.video_repo.find_by_id(video_id)
        if video.owner == user_id:
            return True
        else:
            return False
