import io
import logging
from typing import Optional

from minio import Minio
from minio.error import S3Error

from config_production import settings

logger = logging.getLogger(__name__)


class ObjectStorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as exc:
            logger.error("MinIO bucket check failed: %s", exc)

    def upload_bytes(self, object_name: str, data: bytes, content_type: Optional[str] = None) -> str:
        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream"
        )
        return object_name

    def download(self, object_name: str):
        return self.client.get_object(self.bucket, object_name)

    def health_check(self) -> bool:
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False
