"""
Object storage — Cloudflare R2 (S3-compatible).

R2_* env vars sozlanmagan bo'lsa lokal /uploads/ papkasiga saqlaydi.
Produksiyada R2_ACCOUNT_ID ni .env ga qo'shish yetarli.

Kerakli env vars:
  R2_ACCOUNT_ID         — Cloudflare account ID
  R2_ACCESS_KEY_ID      — R2 API token Access Key ID
  R2_SECRET_ACCESS_KEY  — R2 API token Secret Access Key
  R2_BUCKET_NAME        — bucket nomi (masalan: udx-media)
  R2_PUBLIC_URL         — ommaviy URL (masalan: https://media.udx.uz)
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _r2_configured() -> bool:
    return bool(
        os.getenv("R2_ACCOUNT_ID")
        and os.getenv("R2_ACCESS_KEY_ID")
        and os.getenv("R2_SECRET_ACCESS_KEY")
        and os.getenv("R2_BUCKET_NAME")
    )


async def upload_file(contents: bytes, original_filename: str, content_type: str) -> str:
    """
    Faylni R2 yoki lokal diskka yuklaydi.
    Ommaviy URL qaytaradi.
    """
    ext = Path(original_filename).suffix.lower() or ".bin"
    unique_name = f"{uuid.uuid4()}{ext}"

    if _r2_configured():
        return await _r2_upload(contents, unique_name, content_type)
    return _local_upload(contents, unique_name)


async def _r2_upload(contents: bytes, filename: str, content_type: str) -> str:
    import aioboto3

    account_id = os.getenv("R2_ACCOUNT_ID")
    bucket     = os.getenv("R2_BUCKET_NAME")
    public_url = os.getenv("R2_PUBLIC_URL", "").rstrip("/")
    endpoint   = f"https://{account_id}.r2.cloudflarestorage.com"

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    ) as s3:
        await s3.put_object(
            Bucket=bucket,
            Key=filename,
            Body=contents,
            ContentType=content_type,
        )

    url = f"{public_url}/{filename}" if public_url else f"{endpoint}/{bucket}/{filename}"
    logger.info("[Storage] R2 uploaded: %s", filename)
    return url


def _local_upload(contents: bytes, filename: str) -> str:
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    (upload_dir / filename).write_bytes(contents)
    logger.info("[Storage] Local saved: %s", filename)
    return f"/uploads/{filename}"
