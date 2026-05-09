from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .databases import get_mariadb_connection, get_async_mariadb_connection
from app.db.repositories import AsyncVideoRepository, AsyncUserRepository, AsyncRefreshTokenRepository


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
