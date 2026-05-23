"""HMAC signatures for downloadable blobs."""

from __future__ import annotations

from urllib.parse import parse_qs

from elena.storage.blob import BlobRef, FilesystemBlobStore, verify_signed_download


def test_roundtrip_hmac_signature_matches() -> None:
    secret = "test-secret-at-least-eight-chars-long"
    ref = BlobRef("artifacts/pdf", key="user/x.pdf")
    store = FilesystemBlobStore.__new__(FilesystemBlobStore)  # noqa: PLC0105 — no disk
    q = store.build_download_query(ref, ttl_seconds=120, signing_secret=secret)
    parsed = parse_qs(q.lstrip("?"))
    ns = parsed["namespace"][0]
    ky = parsed["key"][0]
    exp = int(parsed["exp"][0])
    sig = parsed["sig"][0]
    ok, _ = verify_signed_download(secret=secret, namespace=ns, key=ky, exp=exp, sig=sig)
    assert ok is True


def test_reject_expired_hmac() -> None:
    secret = "test-secret-at-least-eight-chars-long"
    ref = BlobRef("artifacts/pdf", key="user/x.pdf")
    store = FilesystemBlobStore.__new__(FilesystemBlobStore)  # noqa: PLC0105
    q = store.build_download_query(ref, ttl_seconds=60, signing_secret=secret)
    parsed = parse_qs(q.lstrip("?"))
    exp = int(parsed["exp"][0]) - 10_000
    ok, reason = verify_signed_download(
        secret=secret,
        namespace=parsed["namespace"][0],
        key=parsed["key"][0],
        exp=exp,
        sig=parsed["sig"][0],
    )
    assert ok is False
    assert reason == "signature_expired"
