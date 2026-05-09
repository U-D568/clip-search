from typing import List, Union, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    CollectionDescription,
    VectorParams,
    Distance,
    Filter,
    PointIdsList,
    FieldCondition,
    MatchValue,
    QueryResponse,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.enums import FrameState
from app.db.models import BaseModel, User, Video, Frame, VideoProgress, FrameProgress
from app.schema.dto import QdrantPoint


### MariaDB ###
class BaseRepository:
    def __init__(self, model: BaseModel, session: Session):
        self.model = model
        self.session = session

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()


class UserRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(User, session)

    def get_by_username(self, username: str) -> User:
        query = self.session.query(self.model).filter(User.username == username)
        user = query.first()
        return user

    def add(self, new_user: User):
        self.session.add(new_user)


class VideoRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(Video, session)

    def add(self, video: Video):
        self.session.add(video)


class VideoProgressRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(VideoProgress, session)

    def add(self, progress: VideoProgress):
        self.session.add(progress)

    def get_by_id(self, video_id: int) -> VideoProgress:
        results = self.session.query(self.model).filter(VideoProgress.key == video_id)
        video_progress = results.first()
        return video_progress


class FrameProgressRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(FrameProgress, session)

    def add(self, progress: FrameProgress):
        self.session.add(progress)

    def add_all(self, progresses: List[FrameProgress]):
        self.session.add_all(progresses)

    def get_by_frame_ids(self, frame_id: List[int]) -> List[FrameProgress]:
        assert len(frame_id) > 0, "frame_id have to be greater than 0"
        query = select(self.model).where(FrameProgress.key.in_(frame_id))
        results = self.session.execute(query)
        return results.scalars().all()

    def get_by_frame_id(self, frame_id: int) -> FrameProgress:
        results = self.session.query(self.model).filter(FrameProgress.key == frame_id)
        video_progress = results.first()
        return video_progress

    def get_not_done(self) -> List[FrameProgress]:
        results = self.session.query(self.model).filter(
            FrameProgress.status != FrameState.DONE
        )
        return results.scalar().all()


class FrameRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(Frame, session)

    def add(self, frame: Frame):
        self.session.add(frame)

    def add_all(self, frames: List[Frame]):
        self.session.add_all(frames)

    def search_by_ids(self, ids: List[int]) -> List[Frame]:
        return self.session.query(Frame).filter(Frame.key.in_(ids)).all()


### Qdrant ###
class QdrantRepository:
    def __init__(self, client: QdrantClient, collection_name: str):
        self.client = client
        self.collection_name = collection_name

    def get_collection(self, collection_name: str):
        res = self.client.get_collection(collection_name)
        return res

    def create_collection(self, collection_name: str, embed_size: int):
        config = VectorParams(size=embed_size, distance=Distance.COSINE)
        return self.client.create_collection(collection_name, vectors_config=config)

    def get_collections(self):
        return self.client.get_collections()

    def upsert_data(self, collection_name: str, data=List[QdrantPoint]):
        return self.client.upsert(collection_name, points=data)

    def delete_by_ids(self, collection_name: str, ids: List[int]):
        selector = PointIdsList(points=ids)
        return self.client.delete(collection_name, points_selector=selector)

    def search_by_id(self, collection_name: str, id=Union[str, int]):
        return self.client.query_points(collection_name, query=id)

    def search(
        self,
        collection_name: str,
        query_vector: Optional[List[float]],
        filter: Filter,
        limit: int,
    ) -> QueryResponse:
        return self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=filter,
            limit=limit,
        )

    def query_image_in_video(
        self,
        collection_name: str,
        text_embeds: List[float],
        video_id: int,
        topk: int = 1,
    ) -> List[float]:
        query_filter = Filter(
            must=[FieldCondition(key="video_id", match=MatchValue(value=video_id))]
        )

        results = self.search(collection_name, text_embeds, query_filter, topk)
        frame_ids = [res.payload.get() for res in results]
        return frame_ids

    def delete(self, collection_name: str, filter: Filter):
        return self.client.delete(collection_name, points_selector=filter)
