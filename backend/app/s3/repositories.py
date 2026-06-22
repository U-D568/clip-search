import os
from typing import BinaryIO
import logging
import io

from botocore.exceptions import ClientError

from app.db.models import Frame, Video


class S3Repositories:
    def __init__(self, client, bucket_name: str):
        self.client = client
        self.bucket_name = bucket_name

    def upload(self, file_obj: BinaryIO, key: str):
        self.client.upload_fileobj(file_obj, self.bucket_name, key)

    def get_url(self, key: str, expiration: int = 3600) -> str:
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logging.error(e)
            return None
        return url

    def download_fileobj(self, key: str) -> io.BytesIO:
        bytesio = io.BytesIO()
        self.client.download_fileobj(self.bucket_name, key, bytesio)
        bytesio.seek(0)
        return bytesio

    def download(self, key: str, path):
        self.client.download_file(self.bucket_name, key, path)
