from app.db.connections import MariaDBConnection
from app.db.repositories import VideoProgressRepository, FrameRepository


def get_video_pregress_repository():
    with MariaDBConnection.get_session() as session:
        return VideoProgressRepository(session)