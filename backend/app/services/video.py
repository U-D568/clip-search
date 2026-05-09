from datetime import datetime
import os
from pathlib import Path
import uuid

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Video, User
from app.db.repositories import AsyncVideoRepository
from app.tasks.cpu_workers import frame_extractor, dummy_queue_test
from app.utils.file import save_video_to_local
from app.exceptions import FileWriteException, DBWriteException, ResourceNotFoundException


class VideoService:
    def __init__(self, video_repo: AsyncVideoRepository):
        self.repo = video_repo

    async def register_video(self, file: UploadFile, user: User):
        # saves to local storage
        dir_path = os.environ["LOCAL_VIDEO_STORAGE"]
        ext = Path(file.filename).suffix
        new_filename = f"{uuid.uuid4()}{ext}"
        save_path = Path(dir_path) / new_filename
        title = Path(file.filename).stem

        try:
            await run_in_threadpool(save_video_to_local, file.file, save_path)

            # update data to database
            new_video = Video(
                file_path=save_path,
                title=title,
                uploaded_time=datetime.now(),
                owner=user.key,
            )
            self.repo.add(new_video)

            await self.repo.commit()
        except FileWriteException:
            if os.path.exists(save_path):
                os.remove(save_path)
            raise FileWriteException("Failed to write file")
        except Exception as err:
            await self.repo.rollback()

            if os.path.exists(save_path):
                os.remove(save_path)

            msg = f"Failed to insert to MariaDB. user_id: {user.key}"
            raise DBWriteException(msg) from err

        frame_extractor.delay(
            str(save_path), new_video.key
        )  # have to change run to delay

    async def find_video(self, video_title: str, user_id: int) -> Video:
        video = await self.repo.find_by_title(video_title, user_id)
        if video is None:
            raise ResourceNotFoundException()
        return video

    async def validate_ownership(self, video_id: int, user_id: int) -> bool:
        video = await self.repo.find_by_id(video_id)
        if video.owner == user_id:
            return True
        else:
            return False
