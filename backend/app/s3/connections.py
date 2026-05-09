import os

import boto3


class S3Connection:
    _client = None
    
    @classmethod
    def init(cls):
        cls._client = boto3.client("s3")

    @classmethod
    def get_client(cls):
        if cls._client is None:
            raise RuntimeError("S3 Client is not initialized")
        return cls._client