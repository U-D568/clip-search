from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    video_uuid: str
    text: str