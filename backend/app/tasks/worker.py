import os

from celery import Celery
from celery.signals import worker_process_init
import dotenv

from app.utils.models import load_clip_vision_model, load_clip_processor
from app.db.connections import MariaDBConnection, QdrantConnection
from app.s3.connections import S3Connection
from app.redis.connections import RedisConnection


@worker_process_init.connect
def init_worker(sender: Celery, **kargs):
    dotenv.load_dotenv(".env")

    worker_type = os.environ.get("WORKER_TYPE", None)

    MariaDBConnection.init()
    S3Connection.init()
    RedisConnection.init()

    if worker_type == "GPU":
        load_clip_vision_model()
        load_clip_processor()
        QdrantConnection.init()


celery_app = Celery(
    "clip-worker",
    broker=os.environ["BROKER_URL"],
    backend=os.environ["BROKER_URL"],
)

celery_app.conf.update(imports=["app.tasks.cpu_workers", "app.tasks.gpu_workers"])
