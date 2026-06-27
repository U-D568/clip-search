from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"


class VideoProgress(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    FRAME_COMPLETE = "f_complete"
    COMPLETE = "complete"
    ERROR = "error"

    @classmethod
    def from_string(cls, value):
        try:
            # finds Enum value corresponsding value automatically
            return cls(value)
        except ValueError:
            return cls.ERROR

class TokenType(Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"


class FrameState(Enum):
    CREATED = "CREATED"
    DONE = "DONE"
    ERROR = "ERROR"
