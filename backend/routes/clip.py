from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.sse import ServerSentEvent, EventSourceResponse

from services.clip import CLIPService
from dependencies.services import get_clip_service
from utils.exceptions import UserNotFoundException, ResourceNotFoundException
from utils.jwt import get_username

video_router = APIRouter(prefix="/clip", tags=["clip"])


@video_router.get("/query/{video_uuid}", response_class=EventSourceResponse)
async def query_frame(
    video_uuid: str,
    query_text: str,
    clip_service: CLIPService = Depends(get_clip_service),
    username: str = Depends(get_username),
):
    if username is None:
        raise HTTPException(401, detail="Invalid Credential.")

    try:
        async for frame_ids in clip_service.query_frame(
            video_uuid, query_text, username
        ):
            yield ServerSentEvent(data=frame_ids)
    except ResourceNotFoundException:
        raise HTTPException(404, detail=f"Unknown Video")
    except UserNotFoundException:
        raise HTTPException(404, detail=f"Unknown User")
