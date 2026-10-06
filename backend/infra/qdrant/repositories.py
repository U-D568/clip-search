from typing import List, Union, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    Filter,
    PointIdsList,
    FieldCondition,
    MatchValue
)

from schema.frame import QdrantPoint


class AsyncQdrantRepository:
    def __init__(self, client: AsyncQdrantClient, collection_name):
        self.client = client
        self.collection_name = collection_name

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

    async def upsert_data(self, data=List[QdrantPoint]):
        return await self.client.upsert(self.collection_name, points=data)

    async def delete_by_ids(self, ids: List[int]):
        selector = PointIdsList(points=ids)
        return await self.client.delete(self.collection_name, points_selector=selector)

    async def get_by_id(self, id=Union[str, int]):
        return await self.client.query_points(self.collection_name, query=id)

    async def query_video(
        self,
        query_vector: Optional[List[float]],
        video_key: int,
        topk=5
    ):
        query_filter = Filter(must=[
            FieldCondition(key="video_key", match=MatchValue(value=video_key))
        ])

        return await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=topk
        )

    async def delete_by_key(self, video_key: int):
        selector = Filter(
            must=[
                FieldCondition(
                    key="video_key",
                    match=MatchValue(value=video_key),
                )
            ]
        )
        return await self.client.delete(
            self.collection_name,
            points_selector=selector,
        )
