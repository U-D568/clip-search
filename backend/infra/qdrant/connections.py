import os

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance


class QdrantConnection:
    _client = None

    @classmethod
    def init(cls):
        if cls._client is None:
            url = get_qdrant_url()
            cls._client = QdrantClient(url)

        ensure_collection(cls._client)

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls.init()
        return cls._client


class AsyncQdrantConnection:
    _client = None

    @classmethod
    def init(cls):
        if cls._client is None:
            url = get_qdrant_url()
            # init() is called from sync contexts (celery signals),
            # so the collection is created with a short-lived sync client
            client = QdrantClient(url)
            try:
                ensure_collection(client)
            finally:
                client.close()
            cls._client = AsyncQdrantClient(url)

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls.init()
        return cls._client


def ensure_collection(client: QdrantClient):
    col_name = os.environ["FRAME_COLLECTION"]
    if not client.collection_exists(col_name):
        embed_size = int(os.environ["DEMENSION"])
        vconfig = VectorParams(size=embed_size, distance=Distance.COSINE)
        client.create_collection(col_name, vectors_config=vconfig)


def get_qdrant_url():
    ip = os.environ["QDRANT_IP"]
    port = os.environ["QDRANT_PORT"]
    url = f"http://{ip}:{port}"
    return url
