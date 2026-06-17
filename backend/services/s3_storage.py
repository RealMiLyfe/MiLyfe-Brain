"""
S3/MinIO file storage for MiLyfe Brain (Phase 3).

Replaces local filesystem for file storage in enterprise deployments.
Supports both AWS S3 and MinIO (S3-compatible, self-hosted).

Configuration:
    STORAGE_BACKEND=local (local|s3)
    S3_ENDPOINT_URL=http://localhost:9000 (MinIO) or omit for AWS S3
    S3_BUCKET_NAME=milyfe-files
    S3_REGION=us-east-1
    AWS_ACCESS_KEY_ID=minioadmin
    AWS_SECRET_ACCESS_KEY=minioadmin
    S3_PREFIX=workspace/
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional

from .logging_config import get_logger

logger = get_logger("storage")

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")


class StorageBackend:
    """Abstract storage backend."""

    async def upload(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    async def download(self, key: str) -> bytes:
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    async def list_files(self, prefix: str = "") -> List[Dict]:
        raise NotImplementedError

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    async def get_metadata(self, key: str) -> Optional[Dict]:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage (development/default)."""

    def __init__(self):
        self.base_dir = Path(os.getenv("WORKSPACE_DIR", "/workspace")) / "storage"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        file_path = self.base_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = data.read() if hasattr(data, "read") else data
        file_path.write_bytes(content)
        logger.debug(f"Local upload: {key}", extra={"size": len(content)})
        return str(file_path)

    async def download(self, key: str) -> bytes:
        file_path = self.base_dir / key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return file_path.read_bytes()

    async def delete(self, key: str) -> bool:
        file_path = self.base_dir / key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def list_files(self, prefix: str = "") -> List[Dict]:
        search_path = self.base_dir / prefix
        files = []
        if search_path.exists():
            for f in search_path.rglob("*"):
                if f.is_file():
                    files.append({
                        "key": str(f.relative_to(self.base_dir)),
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    })
        return files

    async def exists(self, key: str) -> bool:
        return (self.base_dir / key).exists()

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/api/files/{key}"

    async def get_metadata(self, key: str) -> Optional[Dict]:
        file_path = self.base_dir / key
        if not file_path.exists():
            return None
        stat = file_path.stat()
        return {
            "key": key,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_type": "application/octet-stream",
        }


class S3StorageBackend(StorageBackend):
    """AWS S3 / MinIO storage backend."""

    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET_NAME", "milyfe-files")
        self.prefix = os.getenv("S3_PREFIX", "")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")  # None for AWS S3
        self.region = os.getenv("S3_REGION", "us-east-1")
        self._client = None

    def _get_client(self):
        """Get or create S3 client."""
        if self._client is None:
            try:
                import boto3
                kwargs = {
                    "region_name": self.region,
                    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
                    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                }
                if self.endpoint_url:
                    kwargs["endpoint_url"] = self.endpoint_url
                self._client = boto3.client("s3", **kwargs)
            except ImportError:
                raise RuntimeError("Install boto3 for S3 storage: pip install boto3")
        return self._client

    def _full_key(self, key: str) -> str:
        """Get full S3 key with prefix."""
        return f"{self.prefix}{key}" if self.prefix else key

    async def upload(self, key: str, data: BinaryIO, content_type: str = "application/octet-stream") -> str:
        client = self._get_client()
        full_key = self._full_key(key)
        content = data.read() if hasattr(data, "read") else data

        client.put_object(
            Bucket=self.bucket,
            Key=full_key,
            Body=content,
            ContentType=content_type,
        )
        logger.info(f"S3 upload: {full_key}", extra={"bucket": self.bucket, "size": len(content)})
        return f"s3://{self.bucket}/{full_key}"

    async def download(self, key: str) -> bytes:
        client = self._get_client()
        full_key = self._full_key(key)

        response = client.get_object(Bucket=self.bucket, Key=full_key)
        return response["Body"].read()

    async def delete(self, key: str) -> bool:
        client = self._get_client()
        full_key = self._full_key(key)

        try:
            client.delete_object(Bucket=self.bucket, Key=full_key)
            return True
        except Exception:
            return False

    async def list_files(self, prefix: str = "") -> List[Dict]:
        client = self._get_client()
        full_prefix = self._full_key(prefix)

        response = client.list_objects_v2(Bucket=self.bucket, Prefix=full_prefix)
        files = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if self.prefix:
                key = key[len(self.prefix):]
            files.append({
                "key": key,
                "size": obj["Size"],
                "modified": obj["LastModified"].isoformat(),
            })
        return files

    async def exists(self, key: str) -> bool:
        client = self._get_client()
        full_key = self._full_key(key)
        try:
            client.head_object(Bucket=self.bucket, Key=full_key)
            return True
        except Exception:
            return False

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        client = self._get_client()
        full_key = self._full_key(key)

        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": full_key},
            ExpiresIn=expires_in,
        )

    async def get_metadata(self, key: str) -> Optional[Dict]:
        client = self._get_client()
        full_key = self._full_key(key)
        try:
            response = client.head_object(Bucket=self.bucket, Key=full_key)
            return {
                "key": key,
                "size": response["ContentLength"],
                "modified": response["LastModified"].isoformat(),
                "content_type": response.get("ContentType", "application/octet-stream"),
            }
        except Exception:
            return None


def get_storage_backend() -> StorageBackend:
    """Get the configured storage backend."""
    if STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


# Singleton instance
storage = get_storage_backend()
