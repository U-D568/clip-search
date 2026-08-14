import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    Float,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

from utils.enums import UserRole, VideoProgress


class BaseModel(DeclarativeBase):
    pass


class Video(BaseModel):
    __tablename__ = "video"

    __table_args__ = (UniqueConstraint("owner", "title", name="uq_owner_video_title"),)

    # columns
    key = Column(Integer, primary_key=True)
    title = Column(String(512))
    file_path = Column(String(512))
    uploaded_time = Column(DateTime, onupdate=func.current_timestamp())
    owner = Column(Integer, ForeignKey("user.key"), nullable=False)
    uuid = Column(String(36), unique=True, default=uuid.uuid4)
    state = Column(Enum(VideoProgress))

    # relations
    user = relationship("User", back_populates="videos")
    frames = relationship(
        "Frame", back_populates="video", uselist=True, cascade="all, delete-orphan"
    )


class User(BaseModel):
    __tablename__ = "user"

    # columns
    key = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True)
    passwd = Column(String(255))
    role = Column(Enum(UserRole))
    uuid = Column(String(36), unique=True, default=uuid.uuid4)

    # relations
    videos = relationship("Video", back_populates="user", uselist=True)
    refresh_tokens = relationship("RefreshToken", back_populates="user", uselist=True)


class RefreshToken(BaseModel):
    __tablename__ = "refresh_token"

    # columns
    key = Column(Integer, primary_key=True)
    user_key = Column(Integer, ForeignKey("user.key"), nullable=False)
    uuid = Column(String(36), unique=True, default=uuid.uuid4)
    create_at = Column(String(255))
    expire_at = Column(String(255))

    # relations
    user = relationship("User", back_populates="refresh_tokens")


class Frame(BaseModel):
    __tablename__ = "frame"

    # properties
    key = Column(Integer, primary_key=True, autoincrement=True)
    video_key = Column(Integer, ForeignKey("video.key"))
    timestamp = Column(Float)
    index = Column(Integer)
    file_path = Column(String(255))
    uuid = Column(String(36), unique=True, default=uuid.uuid4)

    # relations
    video = relationship("Video", back_populates="frames")
