from infra.db.connections import MariaDBConnection, AsyncMariaDBConnection
from infra.s3.connections import S3Connection
from infra.redis.connections import RedisConnection, AsyncRedisConnection
from infra.qdrant.connections import AsyncQdrantConnection


def get_mariadb_connection():
    with MariaDBConnection.get_session() as session:
        yield session


async def get_async_mariadb_connection():
    async with AsyncMariaDBConnection.get_session_context() as session:
        yield session


def get_s3_client():
    return S3Connection.get_client()


def get_async_qdrant_client():
    return AsyncQdrantConnection.get_client()


def get_redis_client():
    return RedisConnection.get_client()

def get_async_redis_client():
    return AsyncRedisConnection.get_client()
