import os
from typing import BinaryIO

from app.db.models import Frame


class S3Repositories:
    def __init__(self, client, bucket_name: str):
        self.client = client
        self.bucket_name = bucket_name

    def add_frame(self, file_obj: BinaryIO, frame: Frame) -> str:
        frame_prefix = os.environ["FRAME_PREFIX"]
        key = f"{frame_prefix}/{frame.uuid}"
        self.client.upload_fileobj(file_obj, self.bucket_name, key)

        return key
