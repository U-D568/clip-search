from app.db.models import User
from app.db.repositories.async_ import AsyncUserRepository
from app.exceptions import UserNotFoundException


class UserService:
    def __init__(self, user_repo: AsyncUserRepository):
        self.user_repo = user_repo

    async def get_user_by_username(self, username: str) -> User:
        try:
            user = await self.user_repo.get_by_username(username)
            if user is None:
                raise UserNotFoundException()
            return user
        except:
            await self.user_repo.rollback()
            raise

    async def get_user(self, uuid: str) -> User:
        try:
            user = await self.user_repo.get_by_uuid(uuid)
            if user is None:
                raise UserNotFoundException()
            return user
        except:
            await self.user_repo.rollback()
            raise