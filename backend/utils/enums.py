from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"


class VideoProgress(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    EXTRACTED = "extracted"
    COMPLETE = "complete"
    ABORTED = "aborted"
    ERROR = "error"

    # no further state change happens after a terminal state
    @property
    def is_terminal(self) -> bool:
        return self in {
            VideoProgress.COMPLETE,
            VideoProgress.ABORTED,
            VideoProgress.ERROR,
        }

class QueryProgress(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ERROR = "error"

    @property
    def is_terminal(self) -> bool:
        return self in {QueryProgress.COMPLETE, QueryProgress.ERROR}

class TokenType(Enum):
    ACCESS = "ACCESS"
    REFRESH = "REFRESH"
