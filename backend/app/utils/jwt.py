import os
from typing import Optional

from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_token(data: dict) -> str:
    secret = os.environ["JWT_SECRET"]
    hash_algorithm = os.environ["HASH_ALGO"]
    return jwt.encode(data, secret, hash_algorithm)


async def verify_access_token(request: Request) -> bool:
    token = request.cookies.get("access_token")
    if token is None:
        return False

    secret = os.environ["JWT_SECRET"]
    algorithm = os.environ["HASH_ALGO"]
    try:
        payload = jwt.decode(token, secret, algorithm)
        return True
    except JWTError:
        return False


async def get_username(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token is None:
        return None

    secret = os.environ["JWT_SECRET"]
    algorithm = os.environ["HASH_ALGO"]
    try:
        payload = jwt.decode(token, secret, algorithm)
        return payload.get("username")
    except JWTError:
        return None

async def get_user_uuid(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token is None:
        return None

    secret = os.environ["JWT_SECRET"]
    algorithm = os.environ["HASH_ALGO"]
    try:
        payload = jwt.decode(token, secret, algorithm)
        return payload.get("uuid")
    except JWTError:
        return None