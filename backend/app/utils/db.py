import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv(".env")


def get_db_url(is_async=False):
    db_user = os.getenv("MARIADB_USER")
    db_passwd = os.getenv("MARIADB_PASSWORD")
    db_port = os.getenv("MARIADB_PORT")
    db_url = os.getenv("MARIADB_URL")
    schema = os.getenv("MARIADB_DATABASE")
    proto = "mariadb+aiomysql" if is_async else "mariadb+pymysql"
    return f"{proto}://{db_user}:{db_passwd}@{db_url}:{db_port}/{schema}"


def get_qdrant_url():
    ip = os.environ["QDRANT_IP"]
    port = os.environ["QDRANT_PORT"]
    url = f"http://{ip}:{port}"
    return url