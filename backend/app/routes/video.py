from fastapi import APIRouter, UploadFile, HTTPException, Depends, Form, WebSocket
from fastapi.responses import JSONResponse

from app.services.video import VideoService
from app.services.user import UserService
from app.services.clip import CLIPService
from app.dependencies.services import (
    get_video_service,
    get_user_service,
    get_clip_service,
)
from app.exceptions import (
    FileWriteException,
    DBWriteException,
    UserNotFoundException,
    ResourceNotFoundException,
    DuplicatedVideoTitleException,
    AuthenticationException,
)
from app.utils.jwt import get_username

video_router = APIRouter(prefix="/video", tags=["video"])


@video_router.post("/upload")
async def upload_video(
    file: UploadFile,
    title: str = Form(...),
    video_service: VideoService = Depends(get_video_service),
    user_service: UserService = Depends(get_user_service),
    username: str = Depends(get_username),
):
    if username is None:
        raise HTTPException(401, detail=f"Invalid Credential.")
    try:
        user = await user_service.get_user_by_username(username)
        await video_service.register_video(file, title, user)
    except UserNotFoundException:
        raise HTTPException(401, detail=f"Unknown username: {username}")
    except DuplicatedVideoTitleException:
        raise HTTPException(409, detail=f"{title} is already exist.")
    except FileWriteException:
        raise HTTPException(500, detail=f"Failed to save a video {file.filename}")
    except DBWriteException:
        raise HTTPException(500, detail=f"Failed to save a video {file.filename}")

    return JSONResponse({"file_name": file.filename, "result": "ok"}, status_code=200)


@video_router.post("/query")
async def query_frame(
    query_text: str = Form(...),
    video_uuid: str = Form(...),
    clip_service: CLIPService = Depends(get_clip_service),
    video_service: VideoService = Depends(get_video_service),
    user_service: UserService = Depends(get_user_service),
    username: str = Depends(get_username),
):
    try:
        user = await user_service.get_user_by_username(username)
        video = await video_service.find_video_by_uuid(video_uuid, user)
        task_id = clip_service.query_frame(query_text, video, user)
    except ResourceNotFoundException:
        raise HTTPException(403, detail=f"Invalid Access")
    except UserNotFoundException:
        raise HTTPException(403, detail=f"Invalid Access")

    return JSONResponse({"task_id": task_id, "result": "ok"}, status_code=200)


@video_router.post("/query-result")
async def receive_result_webhook(
    websocket: WebSocket,
    task_id: str = Form(...),
    username: str = Depends(get_username),
    user_service: UserService = Depends(get_user_service),
    clip_service: CLIPService = Depends(get_clip_service),
):
    await websocket.accept()
    try:
        user = await user_service.get_user_by_username(username)
        timestamps = await clip_service.get_query_result(task_id, user)
        websocket.send_json({"timestamps": timestamps, "result": "ok"})
    except AuthenticationException:
        raise HTTPException(403, detail=f"Authentication Failed")
    finally:
        websocket.close()
