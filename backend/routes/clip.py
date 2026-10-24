from fastapi import APIRouter, Depends
from fastapi.sse import ServerSentEvent, EventSourceResponse

from services.clip import CLIPService
from dependencies.services import get_clip_service
from utils.exceptions import UserNotFoundException, ResourceNotFoundException
from utils.jwt import require_username

clip_router = APIRouter(prefix="/clip", tags=["clip"])


@clip_router.get("/query/{video_uuid}", response_class=EventSourceResponse)
async def query_frame(
    video_uuid: str,
    query_text: str,
    clip_service: CLIPService = Depends(get_clip_service),
    username: str = Depends(require_username),
):
    try:
        async for frames in clip_service.query_frame(
            video_uuid, query_text, username
        ):
            yield ServerSentEvent(data=frames, event="result")
    except ResourceNotFoundException:
        yield ServerSentEvent(data={"detail": "Unknown Video"}, event="error")
    except UserNotFoundException:
        yield ServerSentEvent(data={"detail": "Unknown User"}, event="error")
    except RuntimeError:
        yield ServerSentEvent(data={"detail": "Search failed"}, event="error")
