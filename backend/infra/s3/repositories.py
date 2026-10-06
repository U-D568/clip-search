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

    def delete_video_files(self, video_file_key: str, frame_uuids: List[str]):
        keys = [
            video_file_key,
            *(f"temp/{frame_uuid}.jpg" for frame_uuid in frame_uuids),
        ]
        self._delete_batch(keys)

    def delete_frame_files(self, frame_uuids: List[str]):
        self._delete_batch([f"temp/{frame_uuid}.jpg" for frame_uuid in frame_uuids])

    def _delete_batch(self, keys: List[str]):
        for start in range(0, len(keys), 1000):
            objects = [{"Key": key} for key in keys[start : start + 1000]]
            if objects:
                response = self._client.delete_objects(
                    Bucket=self._bucket_name,
                    Delete={"Objects": objects, "Quiet": True},
                )
                errors = [
                    error
                    for error in response.get("Errors", [])
                    if error.get("Code")
                    not in {"NoSuchKey", "NoSuchObject", "NotFound"}
                ]
                if errors:
                    raise RuntimeError(f"Failed to delete S3 objects: {errors}")

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

    def download_frame_files(self, frame_uuids: List[str]) -> List[BinaryIO]:
        s3_keys = [f"temp/{frame_uuid}.jpg" for frame_uuid in frame_uuids]
        return self.download_batch_fileobj(s3_keys)

    def download_batch_fileobj(self, s3_keys: List[str], max_workers=4) -> List[BinaryIO]:
        def download_fileobj(key: str) -> BinaryIO:
            bytesio = io.BytesIO()
            self._client.download_fileobj(self._bucket_name, key, bytesio)
            bytesio.seek(0)
            return bytesio
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_iterator = executor.map(download_fileobj, s3_keys)
            for future in future_iterator:
                results.append(future)

        return results

    def download(self, key: str, path):
        self._client.download_file(self._bucket_name, key, path)
