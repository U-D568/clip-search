from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO, List
import logging
import io

from botocore.exceptions import ClientError


class S3Repositories:
    def __init__(self, client, bucket_name: str):
        self._client = client
        self._bucket_name = bucket_name

    def upload(self, file_obj: BinaryIO, key: str):
        self._client.upload_fileobj(file_obj, self._bucket_name, key)

    def batch_upload(self, file_objs: List[BinaryIO], keys: List[str], max_workers=4):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.upload, file_objs, keys)
            executor.shutdown(wait=True)

    def get_url(self, key: str, expiration: int = 1800) -> str:
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logging.error(e)
            return None
        return url

    def download_fileobj(self, key: str) -> BinaryIO:
        bytesio = io.BytesIO()
        self._client.download_fileobj(self._bucket_name, key, bytesio)
        bytesio.seek(0)
        return bytesio

    def download_batch_fileobj(self, keys: List[str], max_workers=4) -> List[BinaryIO]:
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_iterator = executor.map(self.download_fileobj, keys)
            for future in future_iterator:
                results.append(future)

        return results

    def download(self, key: str, path):
        self._client.download_file(self._bucket_name, key, path)
