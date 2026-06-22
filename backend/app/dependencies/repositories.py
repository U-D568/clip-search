import os

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .databases import (
    get_mariadb_connection,
    get_async_mariadb_connection,
    get_s3_client,
)
from app.db.repositories import (
    AsyncVideoRepository,
    AsyncUserRepository,
    AsyncRefreshTokenRepository,
)
from app.s3.repositories import S3Repositories


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


async def get_s3_repository(client=Depends(get_s3_client)) -> S3Repositories:
    bucket_name = os.environ["CLIP_BUCKET_NAME"]
    return S3Repositories(client, bucket_name)
