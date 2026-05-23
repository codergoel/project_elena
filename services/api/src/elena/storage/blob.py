"""Filesystem blob store with HMAC-based download URLs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


@dataclass(frozen=True)
class BlobRef:
    """Pointer under a namespace."""

    namespace: str
    key: str


class BlobStore(ABC):
    """Abstract binary artifact backend."""

    @abstractmethod
    def put_bytes(self, ref: BlobRef, data: bytes) -> None: ...

    @abstractmethod
    def get_bytes(self, ref: BlobRef) -> bytes | None: ...

    @abstractmethod
    def build_download_query(self, ref: BlobRef, ttl_seconds: int, signing_secret: str) -> str: ...


class FilesystemBlobStore(BlobStore):
    """Writes under ``root / namespace / key``."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, ref: BlobRef) -> Path:
        safe_ns = ref.namespace.strip("/ ").replace("..", "")
        rel = Path(safe_ns) / ref.key.strip("/ ").replace("..", "")
        return self.root / rel

    def put_bytes(self, ref: BlobRef, data: bytes) -> None:
        dest = self._path(ref)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    def get_bytes(self, ref: BlobRef) -> bytes | None:
        path = self._path(ref)
        if not path.is_file():
            return None
        return path.read_bytes()

    def build_download_query(self, ref: BlobRef, ttl_seconds: int, signing_secret: str) -> str:
        exp = int(time.time()) + max(60, ttl_seconds)
        sig = sign_download(signing_secret, ref.namespace, ref.key, exp)
        q = (
            f"?namespace={quote(ref.namespace, safe='/')}"
            f"&key={quote(ref.key, safe='/')}&exp={exp}&sig={quote(sig, safe='')}"
        )
        return q


def _b64(msg: bytes) -> str:
    return base64.urlsafe_b64encode(msg).decode("ascii").rstrip("=")


def sign_download(secret: str, namespace: str, key: str, exp: int) -> str:
    raw = f"{namespace}\n{key}\n{exp}".encode()
    return _b64(hmac.new(secret.encode(), raw, hashlib.sha256).digest())


def verify_signed_download(
    *,
    secret: str,
    namespace: str,
    key: str,
    exp: int,
    sig: str,
) -> tuple[bool, str | None]:
    if exp < int(time.time()):
        return False, "signature_expired"
    expect = sign_download(secret, namespace, key, exp)
    if not hmac.compare_digest(expect, sig):
        return False, "bad_signature"
    return True, None
