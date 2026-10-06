from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update

from infra.db.models import BaseModel, User, Video, Frame, VideoProgress, RefreshToken
from utils import enums
from utils.exceptions import UserNotFoundException


class AsyncBaseRepository:
    def __init__(self, model: BaseModel, session: AsyncSession):
        self.model = model
        self.session = session

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


class AsyncUserRepository(AsyncBaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> User:
        query = select(self.model).where(User.username == username)
        response = await self.session.execute(query)
        result = response.scalars().first()
        if result is None:
            raise UserNotFoundException()
        return result

    async def get_by_uuid(self, uuid: str) -> Optional[User]:
        query = select(self.model).where(User.uuid == uuid)
        response = await self.session.execute(query)
        result = response.scalars().first()
        if result is None:
            raise UserNotFoundException()
        return result

    def add(self, new_user: User):
        self.session.add(new_user)


class AsyncRefreshTokenRepository(AsyncBaseRepository):
    def __init__(self, session):
        super().__init__(RefreshToken, session)

    async def get_tokens_by_user(self, uuid: str) -> RefreshToken:
        query = select(self.model).where(RefreshToken.uuid == uuid)
        res = await self.session.execute(query)
        return res.scalars().first()

    def add(self, refresh_token: RefreshToken):
        self.session.add(refresh_token)


class AsyncVideoRepository(AsyncBaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(Video, session)

    def add(self, video: Video):
        self.session.add(video)

    async def find_by_id(self, video_id: int) -> Optional[Video]:
        query = select(self.model).where(Video.key == video_id)
        res = await self.session.execute(query)
        return res.scalars().first()

    async def get_state_by_id(self, video_id: int) -> Optional[enums.VideoProgress]:
        query = select(Video.state).where(Video.key == video_id)
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def find_by_title(self, video_title: str, user_id: int) -> Optional[Video]:
        query = select(self.model).where(
            Video.owner == user_id, Video.title == video_title
        )
        res = await self.session.execute(query)
        return res.scalars().first()

    async def find_by_uuid(self, video_uuid: str, user_id: int) -> Optional[Video]:
        query = select(self.model).where(
            Video.uuid == video_uuid, Video.owner == user_id
        )
        res = await self.session.execute(query)
        video = res.scalars().first()
        return video

    async def find_all_by_user_id(self, user_id: int) -> List[Video]:
        query = select(self.model).where(
            Video.owner == user_id,
            Video.state != enums.VideoProgress.ABORTED,
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def find_frame_uuids_by_video_id(self, video_id: int) -> List[str]:
        query = select(Frame.uuid).where(Frame.video_key == video_id)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def delete(self, video: Video):
        await self.session.delete(video)

    async def set_state(self, video_id: int, state: enums.VideoProgress):
        stmt = update(Video).where(Video.key == video_id).values(state=state)
        await self.session.execute(stmt)

    # Set the state of the video to the given state if it is not already aborted.
    async def set_state_if_not_aborted(
        self, video_id: int, state: enums.VideoProgress
    ) -> bool:
        stmt = (
            update(Video)
            .where(
                Video.key == video_id,
                Video.state != enums.VideoProgress.ABORTED,
            )
            .values(state=state)
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

class AsyncVideoProgressRepository(AsyncBaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(VideoProgress, session)

    async def add(self, progress: VideoProgress):
        await self.session.add(progress)


class AsyncFrameRepository(AsyncBaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(Frame, session)

    def add(self, frame: Frame):
        self.session.add(frame)

    def add_all(self, frames: List[Frame]):
        self.session.add_all(frames)

    async def search_by_ids(self, ids: List[int]) -> List[Frame]:
        query = select(Frame).where(Frame.key.in_(ids))
        res = await self.session.execute(query)
        return res.scalars().all()

    async def delete_by_ids(self, ids: List[int]):
        if ids:
            await self.session.execute(delete(Frame).where(Frame.key.in_(ids)))
