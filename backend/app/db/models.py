import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship, mapped_column, Mapped
from sqlalchemy.sql import func

from ..enums import UserRole, FrameState


class BaseModel(DeclarativeBase):
    pass


class Video(BaseModel):
    __tablename__ = "video"

    __table_args__ = (
        UniqueConstraint('owner', 'title', name='uq_owner_video_title'),
    )

    # columns
    key = Column(Integer, primary_key=True)
    title = Column(String(512))
    file_path = Column(String(512))
    uploaded_time = Column(DateTime, onupdate=func.current_timestamp)
    owner = Column(Integer, ForeignKey("user.key"), nullable=False)
    uuid = Column(String(36), unique=True, default=uuid.uuid4)

    # relations
    user = relationship("User", back_populates="videos")
    frames = relationship(
        "Frame", back_populates="video", uselist=True, cascade="all, delete-orphan"
    )
    progress = relationship("VideoProgress", back_populates="video")


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
    status = relationship("FrameProgress", back_populates="frame", uselist=True)


class FrameProgress(BaseModel):
    __tablename__ = "frame_progress"

    # properties
    key = Column(Integer, primary_key=True, autoincrement=True, index=True)
    frame_key = Column(Integer, ForeignKey("frame.key"), index=True)
    status = Column(Enum(FrameState))

    # relations
    frame = relationship("Frame", back_populates="status")


class VideoProgress(BaseModel):
    __tablename__ = "video_state"

    # properties
    key = Column(Integer, ForeignKey("video.key"), primary_key=True)
    processed = Column(Integer)
    total = Column(Integer)

    # relations
    video = relationship("Video", back_populates="progress")
