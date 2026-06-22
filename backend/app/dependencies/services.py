from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import AsyncVideoRepository, AsyncUserRepository, AsyncRefreshTokenRepository
from app.services.video import VideoService
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.clip import CLIPService
from app.s3.repositories import S3Repositories
from .repositories import get_async_video_repository, get_async_user_repository, get_async_refresh_token_repository, get_s3_repository


async def get_video_service(
    repo: AsyncVideoRepository = Depends(get_async_video_repository),
    s3_repo: S3Repositories = Depends(get_s3_repository)
) -> VideoService:
    return VideoService(repo, s3_repo)


async def get_auth_service(
    user_repo: AsyncUserRepository = Depends(get_async_user_repository),
    token_repo: AsyncRefreshTokenRepository = Depends(get_async_refresh_token_repository)
) -> AuthService:
    return AuthService(user_repo, token_repo)


async def get_user_service(user_repo: AsyncUserRepository = Depends(get_async_user_repository)) -> UserService:
    return UserService(user_repo)

async def get_clip_service() -> CLIPService:
    return CLIPService()