from app.db.connections import (
    MariaDBConnection,
    AsyncMariaDBConnection,
    QdrantConnection,
)
from app.s3.connections import S3Connection


def get_mariadb_connection():
    with MariaDBConnection.get_session() as session:
        yield session


async def get_async_mariadb_connection():
    async with AsyncMariaDBConnection.get_session() as session:
        yield session

def get_s3_client():
    return S3Connection.get_client()