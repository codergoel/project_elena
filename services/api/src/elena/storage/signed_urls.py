"""Build public signed download URLs for blob artifacts."""

from __future__ import annotations

from elena.config import Settings
from elena.storage.blob import BlobRef, BlobStore


def public_signed_download_url(
    *,
    blobs: BlobStore,
    settings: Settings,
    namespace: str,
    key: str,
    ttl_seconds: int = 3600,
) -> str:
    q = blobs.build_download_query(
        BlobRef(namespace=namespace, key=key),
        ttl_seconds=ttl_seconds,
        signing_secret=settings.file_download_signing_secret,
    )
    root = settings.public_api_base_url.rstrip("/")
    return f"{root}/api/v1/files/download{q}"
