from contextlib import contextmanager, asynccontextmanager
import os
from typing import Generator, AsyncGenerator


from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.utils.db import get_db_url, get_qdrant_url


### MariaDB ###
# async db configuration
class AsyncMariaDBConnection:
    _engine = None
    _session_factory = None

    @classmethod
    def init(cls):
        if cls._engine is None:
            cls._engine = create_async_engine(
                get_db_url(is_async=True),
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,
                pool_pre_ping=True,
            )

        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                bind=cls._get_engine(), expire_on_commit=False, class_=AsyncSession
            )

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            raise RuntimeError("Async MariaDB Connection is not initialized.")
        return cls._engine

    @classmethod
    def _get_session_factory(cls):
        if cls._session_factory is None:
            raise RuntimeError("Async Session Factory is not initialized.")
        return cls._session_factory

    @classmethod
    @asynccontextmanager
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        session_factory = cls._get_session_factory()
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()


# sync db configuration
class MariaDBConnection:
    _engine = None
    _session_factory = None

    @classmethod
    def init(cls):
        if cls._engine is None:
            cls._engine = create_engine(
                get_db_url(), pool_size=5, pool_recycle=3600, pool_pre_ping=True
            )

        if cls._session_factory is None:
            cls._session_factory = sessionmaker(
                bind=cls._get_engine(), autocommit=False, autoflush=False
            )

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            raise RuntimeError("MariaDB engine is not initialized.")
        return cls._engine

    @classmethod
    def _get_session_factory(cls) -> Session:
        if cls._session_factory is None:
            raise RuntimeError("Sync session factoy is not initalized.")
        return cls._session_factory

    @classmethod
    @contextmanager
    def get_session(cls) -> Generator[Session, None, None]:
        session_factory = cls._get_session_factory()
        session = session_factory()
        try:
            yield session
        finally:
            session.close()


### Qdrant ###
class QdrantConnection:
    _client = None

    @classmethod
    def init(cls, is_async=False):
        if cls._client is None:
            url = get_qdrant_url()

            if is_async:
                cls._client = AsyncQdrantClient(url)
            else:
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
            raise RuntimeError("Qdrant Client is not initalized")
        return cls._client
