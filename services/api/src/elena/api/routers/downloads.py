"""Signed URLs for blobs stored via :mod:`elena.storage.blob`."""

from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from elena.api.deps import BlobStoreDep, SettingsDep
from elena.storage.blob import BlobRef, verify_signed_download

router = APIRouter(tags=["downloads"])


def _download_headers(*, blob_key: str) -> tuple[str, str]:
    """Return ``(media_type, Content-Disposition)`` for blob bytes."""

    name = PurePosixPath(blob_key).name.lower()
    if name.endswith(".txt"):
        return (
            "text/plain; charset=utf-8",
            f'attachment; filename="{PurePosixPath(blob_key).name}"',
        )
    if name.endswith(".pdf"):
        return "application/pdf", 'attachment; filename="document.pdf"'
    return "application/octet-stream", 'attachment; filename="download"'


@router.get("/files/download")
async def download_blob(
    blobs: BlobStoreDep,
    settings: SettingsDep,
    namespace: str = Query(description="blob namespace prefix"),
    key: str = Query(description="blob key path under namespace"),
    exp: int = Query(ge=0, description="unix expiry timestamp"),
    sig: str = Query(description="HMAC digest from signing secret"),
) -> Response:
    ok, reason = verify_signed_download(
        secret=settings.file_download_signing_secret,
        namespace=namespace,
        key=key,
        exp=exp,
        sig=sig,
    )
    if not ok:
        raise HTTPException(status_code=403, detail=reason)

    ref = BlobRef(namespace=namespace, key=key)
    payload = blobs.get_bytes(ref)
    if payload is None:
        raise HTTPException(status_code=404, detail="blob not found")

    media_type, disposition = _download_headers(blob_key=key)
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )
