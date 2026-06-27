class BaseException(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class FileWriteException(BaseException):
    pass


class DBWriteException(BaseException):
    pass


class DBReadException(BaseException):
    pass


class UserAlreadyExistException(BaseException):
    pass


class UserNotFoundException(BaseException):
    pass

class VideoNotFoundException(BaseException):
    pass

class InvalidCredentialsException(BaseException):
    pass


class UUIDGenerationException(BaseException):
    pass


class CollectionNotFoundException(BaseException):
    pass

class ResourceNotFoundException(BaseException):
    pass

class DuplicatedVideoTitleException(BaseException):
    pass

class AuthenticationException(BaseException):
    pass