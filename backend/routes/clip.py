from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.sse import ServerSentEvent, EventSourceResponse

from schema.requests import QueryRequest
from services.clip import CLIPService
from dependencies.services import get_clip_service
from utils.exceptions import (
    UserNotFoundException,
    ResourceNotFoundException,
    AuthenticationException,
)
from utils.jwt import get_username

video_router = APIRouter(prefix="/clip", tags=["clip"])


@video_router.post("/query/{video_uuid}")
async def query_frame(
    video_uuid: str,
    query_text: str,
    clip_service: CLIPService = Depends(get_clip_service),
    username: str = Depends(get_username),
):
    try:
        task_uuid = await clip_service.query_frame(video_uuid, query_text, username)
    except ResourceNotFoundException:
        raise HTTPException(404, detail=f"Unknown Video")
    except UserNotFoundException:
        raise HTTPException(404, detail=f"Unknown User")

    return JSONResponse({"task_id": task_uuid, "result": "ok"}, status_code=200)


@video_router.get("/response/{task_uuid}", response_class=EventSourceResponse)
async def get_query_response(
    task_uuid: str,
    clip_service: CLIPService = Depends(get_clip_service),
    username: str = Depends(get_username),
):
    if username is None:
        raise HTTPException(401, detail="Invalid Credential.")

    async for frame_ids in clip_service.get_query_result(task_uuid, username):
        yield ServerSentEvent(data=frame_ids)
