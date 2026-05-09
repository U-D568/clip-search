from fastapi import APIRouter, Depends
from app.utils.jwt import get_current_username

from app.tasks.cpu_workers import dummy_queue_test

test_router = APIRouter(prefix="/test", tags=["test"])


@test_router.get("/test")
async def test():
    dummy_queue_test.delay("Hello world!")
    return "Done"
