from typing import List, Union, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    Filter,
    PointIdsList,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import BaseModel, User, Video, Frame, VideoProgress, RefreshToken
from app.schema.dto import QdrantPoint


### MariaDB ###
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

    async def get_by_username(self, username: str) -> Optional[User]:
        query = select(self.model).where(User.username == username)
        res = await self.session.execute(query)
        return res.scalars().first()

    async def get_by_uuid(self, uuid: str) -> Optional[User]:
        query = select(self.model).where(User.uuid == uuid)
        res = await self.session.execute(query)
        return res.scalars().first()

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
    
    async def find_by_title(self, video_title: str, user_id: int) -> Optional[Video]:
        query = select(self.model).where(Video.owner == user_id, Video.title == video_title)
        res = await self.session.execute(query)
        return res.scalars().first()
    
    async def find_by_uuid(self, video_uuid: str, user_id: int) -> Optional[Video]:
        query = select(self.model).where(Video.uuid == video_uuid, Video.owner == user_id)
        res = await self.session.execute(query)
        video = res.scalars().first()
        return video


class AsyncVideoProgressRepository(AsyncBaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(VideoProgress, session)

    def add(self, progress: VideoProgress):
        self.session.add(progress)


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


### Qdrant ###
class AsyncQdrantRepository:
    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def get_collection(self, collection_name: str):
        res = await self.client.get_collection(collection_name)
        return res

    async def get_collections(self):
        return await self.client.get_collections()

    async def create_collection(self, collection_name: str, embed_size: int):
        config = VectorParams(size=embed_size, distance=Distance.COSINE)
        return await self.client.create_collection(
            collection_name, vectors_config=config
        )

    async def upsert_data(self, collection_name: str, data=List[QdrantPoint]):
        return await self.client.upsert(collection_name, points=data)

    async def delete_by_ids(self, collection_name: str, ids: List[int]):
        selector = PointIdsList(points=ids)
        return await self.client.delete(collection_name, points_selector=selector)

    async def search_by_id(self, collection_name: str, id=Union[str, int]):
        return await self.client.query_points(collection_name, query=id)

    async def search(
        self,
        collection_name: str,
        query_vector: Optional[List[float]],
        filter: Filter,
    ):
        return await self.client.query_points(
            collection_name=collection_name, query=query_vector, query_filter=filter
        )

    async def delete(self, collection_name: str, filter: Filter):
        return await self.client.delete(collection_name, points_selector=filter)
