from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"


class VideoProgress(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ERROR = "error"


class TokenType(Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"


class FrameState(Enum):
    CREATED = "CREATED"
    DONE = "DONE"
    ERROR = "ERROR"
