from datetime import datetime, timedelta
import os
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.db.repositories.async_ import AsyncUserRepository, AsyncRefreshTokenRepository
from app.utils.jwt import create_token
from app.utils.auth import verify_passwd
from app.exceptions import InvalidCredentialsException
from app.db.models import User, RefreshToken
from app.enums import TokenType, UserRole
from app.utils.auth import hash_password
from app.exceptions import (
    UUIDGenerationException,
    DBReadException,
    DBWriteException,
    UserAlreadyExistException,
)

UUID_RETRIES = 3


class AuthService:
    def __init__(
        self,
        user_repo: AsyncUserRepository,
        refresh_token_repo: AsyncRefreshTokenRepository,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo

    async def login(self, username: str, passwd: str) -> User:
        # tries to find user
        try:
            user = await self.user_repo.get_by_username(username)
        except:
            raise DBReadException()

        # user not found
        if user is None:
            raise InvalidCredentialsException()

        # password mismatch
        if not verify_passwd(passwd, user.passwd):
            raise InvalidCredentialsException()

        return user

    async def register(
        self, username: str, passwd: str, role: UserRole = UserRole.USER
    ):
        new_user = User(username=username, passwd=hash_password(passwd), role=role)
        self.user_repo.add(new_user)
        try:
            await self.user_repo.commit()
        except IntegrityError:
            await self.user_repo.rollback()
            raise UserAlreadyExistException()
        except:
            await self.user_repo.rollback()
            raise DBReadException()

    def create_access_token(self, user: User):
        seconds = int(os.environ["ACCESS_TOKEN_EXPIRE"])
        expire_at = datetime.now() + timedelta(seconds=seconds)
        create_at = datetime.now()
        uuid = str(uuid4())

        data = {
            "uuid": uuid,
            "username": user.username,
            "exp": expire_at,
            "type": TokenType.ACCESS.value,
            "iat": create_at,  # issused at time
        }

        return create_token(data)

    async def create_refresh_token(self, user: User):
        seconds = int(os.environ["REFRESH_TOKEN_EXPIRE"])
        expire_at = datetime.now() + timedelta(seconds=seconds)
        create_at = datetime.now()

        for _ in range(UUID_RETRIES):
            try:
                uuid = str(uuid4())
                token = RefreshToken(
                    uuid=uuid, user_key=user.key, create_at=create_at, expire_at=expire_at
                )
                self.refresh_token_repo.add(token)
                await self.refresh_token_repo.commit()
                break
            except IntegrityError:
                continue
            except Exception as err:
                await self.refresh_token_repo.rollback()
                raise UUIDGenerationException()

        data = {
            "uuid": uuid,
            "username": user.username,
            "exp": expire_at,
            "type": TokenType.ACCESS.value,
            "iat": create_at,
        }

        return create_token(data)
