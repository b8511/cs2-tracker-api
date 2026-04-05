"""
Cloudflare R2 storage service (S3-compatible via boto3).
Used as image fallback when csgodatabase.com is unavailable,
and as the target for the seed script.
"""

import os
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("R2_SECRET_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def _bucket() -> str:
    return os.getenv("R2_BUCKET", "cs2-images")


def get_image(key: str) -> bytes | None:
    """Fetch an image from R2 by key. Returns bytes or None if not found."""
    try:
        resp = _get_client().get_object(Bucket=_bucket(), Key=key)
        return resp["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise
    except (ValueError, Exception):
        return None


def put_image(key: str, data: bytes, content_type: str = "image/webp") -> None:
    """Upload an image to R2."""
    _get_client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="public, max-age=31536000",  # 1 year — immutable images
    )


def is_configured() -> bool:
    """Return True if all R2 env vars are present and not placeholder values."""
    values = [os.getenv(k, "") for k in ("R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_BUCKET")]
    return all(v and "<" not in v for v in values)
