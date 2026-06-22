from fastapi import APIRouter, UploadFile, HTTPException, Depends
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
    DuplicatedVideoTitleException
)
from app.utils.jwt import get_current_username, get_user_uuid

video_router = APIRouter(prefix="/video", tags=["video"])


@video_router.post("/upload")
async def upload_video(
    file: UploadFile,
    title: str,
    video_service: VideoService = Depends(get_video_service),
    user_service: UserService = Depends(get_user_service),
    username: str = Depends(get_current_username),
):
    if username is None:
        raise HTTPException(401, detail=f"Invalid Credential.")
    try:
        user = await user_service.get_user_by_username(username)
    except UserNotFoundException:
        raise HTTPException(401, detail=f"Unknown username: {username}")

    try:
        await video_service.register_video(file, title, user)
    except DuplicatedVideoTitleException:
        raise HTTPException(409, detail=f"{title} is already exist.")
    except FileWriteException:
        raise HTTPException(500, detail=f"Failed to save a video {file.filename}")
    except DBWriteException:
        raise HTTPException(500, detail=f"Failed to save a video {file.filename}")

    return JSONResponse({"file_name": file.filename, "result": "ok"}, status_code=200)


@video_router.post("/query")
async def query_frame(
    query_text: str,
    video_title: str,
    clip_service: CLIPService = Depends(get_clip_service),
    video_service: VideoService = Depends(get_video_service),
    user_service: UserService = Depends(get_user_service),
    uuid: str = Depends(get_user_uuid),
):
    # validates video ownership
    user_id = await user_service.get_user_id(uuid)

    try:
        video = await video_service.find_video(video_title, user_id)
        clip_service.query_frame(query_text, video.key)
    except ResourceNotFoundException:
        raise HTTPException(403, detail=f"Invalid Access")

    # top 5 frame_url 반환
    return JSONResponse({""})
