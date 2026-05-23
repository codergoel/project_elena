# Privacy and data locations (Phase 9.4 scaffold)

High-level pointers for ops and retention policy work; adjust with legal review.

## What we store today

| Data | Typical location | Deleted when |
| --- | --- | --- |
| User row | Postgres `users` | No automated “delete account” flow yet (*Phase 9.4 backlog*); rows can be removed manually. |
| Base / variant / threads | Postgres `base_resumes`, `variants`, `conversation_threads`, `resume_documents` | `DELETE /bases/{id}` (after variants); `DELETE /variants/{id}`. Rows cascade children per FKs/migrations. |
| Import PDF + JD blobs | Filesystem blob store under `imports/{user}`, `jd/{user}` (see `FilesystemBlobStore`) | Orphan blobs are **not** automatically GC’d (*backlog*: retention job keyed by FK paths). |
| Rendered PDFs | `artifacts/pdf/{user}/{document}/…` | Not auto-pruned (*backlog*: TTL sweep or LRU). |

## Backups / export

- **`GET /api/v1/bases/{id}/export`** and **`GET /api/v1/variants/{id}/export`** return the active `ResumeDocument` envelope JSON plus metadata (`Phase 9.3`).
- PDFs remain behind signed URLs; keep signing secret out of logs and traces.

## Logging hygiene

- Do not log Gemini keys, JWTs, or raw signed download query strings (`Phase 9.1` ongoing).
- HTTP responses include **`X-Request-ID`** for correlating API logs with browser reports (`Phase 10` lite).
