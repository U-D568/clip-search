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

        client = cls.get_client()
        col_name = os.environ["FRAME_COLLECTION"]
        if not client.collection_exists(col_name):
            embed_size = os.environ["DEMENSION"]
            vconfig = VectorParams(size=embed_size, distance=Distance.COSINE)
            client.create_collection(col_name, vconfig)

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
            cls._client = AsyncQdrantClient(url)

        client = cls.get_client()
        col_name = os.environ["FRAME_COLLECTION"]
        if not client.collection_exists(col_name):
            embed_size = os.environ["DEMENSION"]
            vconfig = VectorParams(size=embed_size, distance=Distance.COSINE)
            client.create_collection(col_name, vconfig)

    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls.init()
        return cls._client


def get_qdrant_url():
    ip = os.environ["QDRANT_IP"]
    port = os.environ["QDRANT_PORT"]
    url = f"http://{ip}:{port}"
    return url
