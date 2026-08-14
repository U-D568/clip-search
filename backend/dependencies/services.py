from fastapi import Depends

from infra.db.repositories import (
    AsyncVideoRepository,
    AsyncUserRepository,
    AsyncRefreshTokenRepository,
)
from infra.qdrant.repositories import AsyncQdrantRepository
from infra.s3.repositories import S3Repositories
from infra.redis.repositories import VideoRedisRepository
from .repositories import (
    get_async_video_repository,
    get_async_user_repository,
    get_async_refresh_token_repository,
    get_s3_repository,
    get_async_qdrant_reposiroty,
    get_redis_video_repository,
)
from services.video import VideoService
from services.auth import AuthService
from services.user import UserService
from services.clip import CLIPService


async def get_video_service(
    repo: AsyncVideoRepository = Depends(get_async_video_repository),
    s3_repo: S3Repositories = Depends(get_s3_repository),
    qdrant_repo: AsyncQdrantRepository = Depends(get_async_qdrant_reposiroty),
    redis_repo: VideoRedisRepository = Depends(get_redis_video_repository),
) -> VideoService:
    return VideoService(repo, s3_repo, qdrant_repo, redis_repo)


async def get_auth_service(
    user_repo: AsyncUserRepository = Depends(get_async_user_repository),
    token_repo: AsyncRefreshTokenRepository = Depends(
        get_async_refresh_token_repository
    ),
) -> AuthService:
    return AuthService(user_repo, token_repo)


async def get_user_service(
    user_repo: AsyncUserRepository = Depends(get_async_user_repository),
) -> UserService:
    return UserService(user_repo)


async def get_clip_service() -> CLIPService:
    return CLIPService()
