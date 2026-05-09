from app.db.connections import (
    MariaDBConnection,
    AsyncMariaDBConnection,
    QdrantConnection,
)


def get_mariadb_connection():
    with MariaDBConnection.get_session() as session:
        yield session


async def get_async_mariadb_connection():
    async with AsyncMariaDBConnection.get_session() as session:
        yield session
