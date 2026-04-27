"""
src/ragapp/storage/s3.py

S3 implementation of DocumentStore.
"""

import asyncio
from functools import partial
from typing import Any

import boto3
from botocore.exceptions import ClientError

from ragapp.storage.base import DocumentStore


class S3DocumentStore(DocumentStore):
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self._client = boto3.client("s3", region_name=region)
        self._bucket = bucket_name

    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        await self._run(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def download(self, key: str) -> bytes:
        response = await self._run(self._client.get_object, Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        await self._run(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def exists(self, key: str) -> bool:
        try:
            await self._run(self._client.head_object, Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        response = await self._run(
            self._client.list_objects_v2,
            Bucket=self._bucket,
            Prefix=prefix,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]
