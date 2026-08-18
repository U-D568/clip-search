import asyncio
import os

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
import dotenv

from ai.models.clip import load_clip_vision_model, load_clip_processor
from infra.db.connections import AsyncMariaDBConnection
from infra.qdrant.connections import AsyncQdrantConnection
from infra.s3.connections import S3Connection
from infra.redis.connections import RedisConnection


@worker_process_init.connect
def on_init(sender: Celery, **kargs):
    dotenv.load_dotenv(".env")

    worker_type = os.environ.get("DEVICE_TYPE", None)

    AsyncMariaDBConnection.init()
    AsyncQdrantConnection.init()
    S3Connection.init()
    RedisConnection.init()
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)

    if worker_type == "GPU":
        load_clip_vision_model()
        load_clip_processor()


@worker_process_shutdown.connect
def on_shutdown(sender: Celery, **kargs):
    AsyncMariaDBConnection.close()
    AsyncQdrantConnection.close()
    S3Connection.close()
    RedisConnection.close()
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.close()
    except:
        pass


celery_app = Celery(
    "clip-worker",
    broker=os.environ["BROKER_URL"],
    backend=os.environ["BROKER_URL"],
)

celery_app.conf.update(
    imports=[
        "workers.workers.frame_extractor",
        "workers.workers.image_embedder",
        "workers.workers.text_embedder",
    ]
)
