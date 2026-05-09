from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.dependencies.services import get_auth_service
from app.schema.dto import LoginRequest
from app.exceptions import InvalidCredentialsException, UserAlreadyExistException
from app.services.auth import AuthService
from app.exceptions import DBReadException


auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login")
async def login(
    login_request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
):
    try:
        user = await service.login(login_request.username, login_request.password)
    except InvalidCredentialsException as e:
        raise HTTPException(401, "Invalid credentials")

    response = JSONResponse(
        {"username": login_request.username, "result": "ok"}, status_code=200
    )

    access_token = service.create_access_token(user)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    refresh_token = await service.create_refresh_token(user)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )

    return response


@auth_router.post("/register")
async def register(
    user_data: LoginRequest, service: AuthService = Depends(get_auth_service)
):
    try:
        await service.register(user_data.username, user_data.password)
    except UserAlreadyExistException:
        return HTTPException(401, "User Already Exists")
    except DBReadException:
        return HTTPException(500, "Failed to make a new account")

    return JSONResponse({"username": user_data.username}, status_code=200)
