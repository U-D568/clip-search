from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.routes.video import video_router
from app.routes.auth import auth_router
from app.db.connections import (
    MariaDBConnection,
    AsyncMariaDBConnection,
    QdrantConnection,
)
from app.db.models import BaseModel, User
from app.enums import UserRole
from app.s3.connections import S3Connection


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # incldes routers
    app.include_router(video_router)
    app.include_router(auth_router)

    # CORS
    allow_origins = ["http://localhost:8000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # CSRF

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    on_init()
    yield
    on_exit()


def on_init():
    # DB Initalization
    AsyncMariaDBConnection.init()

    # Development code
    MariaDBConnection.init()
    engine = MariaDBConnection._get_engine()
    BaseModel.metadata.create_all(bind=engine)

    # local video storage
    path = os.environ["LOCAL_VIDEO_STORAGE"]
    os.makedirs(path, exist_ok=True)

    # S3 Initalization
    S3Connection.init()


def on_exit():
    pass


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
