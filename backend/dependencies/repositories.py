import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .connections import (
    get_async_mariadb_connection,
    get_s3_client,
    get_async_qdrant_client,
    get_redis_client,
)
from infra.db.repositories import (
    AsyncVideoRepository,
    AsyncUserRepository,
    AsyncRefreshTokenRepository,
    AsyncFrameRepository,
)
from infra.qdrant.repositories import AsyncQdrantRepository
from infra.redis.repositories import (
    AsyncRedisVideoRepository,
    AsyncRedisQueryRepository,
)
from infra.s3.repositories import S3Repositories


async def get_async_video_repository(
    session: AsyncSession = Depends(get_async_mariadb_connection),
) -> AsyncVideoRepository:
    return AsyncVideoRepository(session)


async def get_async_user_repository(
    session: AsyncSession = Depends(get_async_mariadb_connection),
) -> AsyncUserRepository:
    return AsyncUserRepository(session)


async def get_async_refresh_token_repository(
    session: AsyncSession = Depends(get_async_mariadb_connection),
) -> AsyncRefreshTokenRepository:
    return AsyncRefreshTokenRepository(session)


async def get_async_frame_repository(
    session: AsyncSession = Depends(get_async_mariadb_connection),
) -> AsyncFrameRepository:
    return AsyncFrameRepository(session)


async def get_s3_repository(client=Depends(get_s3_client)) -> S3Repositories:
    bucket_name = os.environ["CLIP_BUCKET_NAME"]
    return S3Repositories(client, bucket_name)


async def get_async_qdrant_reposiroty(
    client=Depends(get_async_qdrant_client),
) -> AsyncQdrantRepository:
    collection_name = os.environ["FRAME_COLLECTION"]
    return AsyncQdrantRepository(client, collection_name)


async def get_async_redis_video_repository(
    client=Depends(get_redis_client),
) -> AsyncRedisVideoRepository:
    return AsyncRedisVideoRepository(client)


async def get_async_redis_query_repository(
    client=Depends(get_redis_client),
) -> AsyncRedisQueryRepository:
    return AsyncRedisQueryRepository(client)
