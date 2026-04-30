# Tech stack (decision) — Project Elena

**Status:** Proposed for v1 deployable product  
**Related:** [PRODUCT_ONEPAGER.md](./PRODUCT_ONEPAGER.md), [VERSIONING_MODEL.md](./VERSIONING_MODEL.md)  
**Last updated:** 2026-04-30 (v0.3 — repo path note in §9)

This document records **concrete** choices for a **hosted web platform** with a **Bring Your Own API Key (BYOK)** model: users connect their own LLM provider keys; the product never **requires** platform-funded inference for core flows.

---

## 1. Principles

| Principle | Implication |
|-----------|-------------|
| **Agent runtime in Python** | Deep Agents + LangGraph are first-class in Python. The **serving** layer for agents should be **Python** (or a thin gRPC/HTTP wrapper in another language is unnecessary for v1). |
| **BYOK first** | Keys are **per user**, **encrypted at rest**, used only in request workers, **never** logged or returned in APIs. |
| **Separation of UI and compute** | **Browser** = editor, chat, PDF view. **API + workers** = authz, storage, LLM calls (with user key), LaTeX sandbox. |
| **Boring at scale** | **Postgres** + **S3-compatible** blobs + **containers** for LaTeX. Avoid custom databases for v1. |
| **Match LangGraph deployment patterns** | Use supported **checkpointers** and **streaming** APIs; understand **Agent Server** vs self-hosted (see §4.1). |

---

## 2. High-level architecture

```text
[Browser: Next.js]  --HTTPS-->  [API: FastAPI]
                                    |
                    +---------------+---------------+
                    |               |               |
                [Postgres]     [Object store]   [Redis] (queue / rate limits)
                    |               |               |
                    +-------+-------+               |
                            |                       |
                    [Agent + tools in API or worker] |
                    (reads user key from store, decrypt in memory) |
                            |                                    |
                    [LaTeX job runner: Docker/queue]  <------------+
                    (no LLM; isolated compile)
```

---

## 3. Frontend (web)

| Layer | Choice | Rationale |
|------|--------|-----------|
| **Framework** | **Next.js** (App Router) **or** **Vite + React** | **Next.js** if you want one deploy target (Vercel) + good DX; **Vite** if the Python API is the only backend and you want a simpler SPA. **Recommendation: Next.js 15+ (App Router)** for routing, API routes (optional for BFF), and streaming-friendly patterns. |
| **Language** | **TypeScript** (strict) | Type safety for complex editor and chat UIs. |
| **Styling** | **Tailwind CSS** | Fast UI iteration; one-page + split-pane layouts. |
| **Components** | **shadcn/ui** (Radix) | Accessible primitives; easy to make “resume viewer + chat” chrome. |
| **PDF preview** | **react-pdf** (PDF.js) or **iframe** to signed URL | Prefer **signed short-lived URLs** from your API to the stored PDF. |
| **Data fetching** | **TanStack Query** + native **fetch** / **openapi-fetch** (if you generate a client) | Caching, retries for resume metadata. |
| **Chat / streams** | **Vercel AI SDK**-style **SSE** consumer **or** manual `EventSource` / `fetch` stream | Must align with FastAPI `StreamingResponse` (SSE) for agent tokens. |
| **State (light)** | **Zustand** or **Jotai** (optional) | For active base/variant and UI panes; avoid global Redux for v1 unless needed. |

**Deployment:** **Vercel** (Next) or **Cloudflare Pages** (Vite static + separate API host); configure **CORS** and **env** for API URL.

---

## 4. Backend API and agent service

| Layer | Choice | Rationale |
|------|--------|-----------|
| **API framework** | **FastAPI** | Async, OpenAPI, first-class support for **SSE** streaming, fits **LangGraph**’s ainvoke/stream patterns. |
| **Runtime** | **Python 3.12+** | |
| **Agent framework** | **Deep Agents** (`create_deep_agent`) on **LangGraph** | As per product architecture; **checkpointer** backed by **Postgres** in production (see below). |
| **LLM routing** | **User keys → LangChain `init_chat_model` / provider packages** or **LiteLLM** in-process (optional) | **BYOK:** resolve **per-request** from encrypted store. LiteLLM helps normalize `provider:model` strings; adds a dependency—acceptable if you want one abstraction. |
| **ID / typing** | **Pydantic v2** | Matches LangChain; request/response models. |
| **Migrations / ORM** | **SQLAlchemy 2.0** + **Alembic** **or** **SQLModel** | Mature, Postgres-friendly. **SQLModel** is faster to wire if team is small. |
| **Task queue (optional v1, likely v1.1)** | **Celery + Redis** **or** **Dramatiq** **or** **ARQ** | Long agent runs and LaTeX jobs can **block** a web worker; moving compile + some agent invocations to **workers** improves tail latency. **MVP** can run agent in API with **timeouts** and add queue when needed. |
| **LaTeX** | **Docker** image (TeX Live slim or full) invoked by API/worker; **no network** inside container; CPU/memory **limits** | Complements **sandbox** options documented for Deep Agents (e.g. Daytona, Modal, Runloop) for **untrusted** code; LaTeX compile is a **dedicated** image/queue, not necessarily the same as LLM tool sandbox. See [backends](https://docs.langchain.com/oss/python/deepagents/backends) for harness FS vs execution environments. |

**Deployment (API):** **Fly.io**, **Railway**, **Render**, **Google Cloud Run**, or **AWS ECS Fargate** (API as a service + separate worker if queued).

### 4.1 LangGraph / Deep Agents (official docs alignment)

The following is grounded in the **Docs by LangChain** MCP (same content as the public site).

| Topic | What the docs say | Implication for Elena |
|--------|-------------------|------------------------|
| **Deep Agents on LangGraph** | The harness uses the **LangGraph** runtime: durable runs, **streaming**, human-in-the-loop, etc. ([Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)) | We stay on the **Python** `deepagents` + `LangGraph` path already chosen. |
| **Managed deploy path** | **`deepagents deploy`** (CLI, beta) deploys a **LangSmith Deployment**: scalable server with many endpoints (threads, runs, assistants, optional MCP, optional UI). See [Deploy with the CLI](https://docs.langchain.com/oss/python/deepagents/deploy). | **Useful** if we want a **managed** graph API with **Clerk** or **Supabase** in `[auth]`, optional prebuilt React chat at `/app`, and **execution sandboxes** (e.g. Daytona, Modal, Runloop). **Not a drop-in for BYOK-by-default** (see next row). |
| **Model keys in stock deploy** | `deepagents.toml` sets `model = "provider:model"`. Keys typically live in **`.env`** at the deployment (e.g. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LANGSMITH_API_KEY`). | That pattern is **deployment- or org-level** keys. **Elena's BYOK** = **end-user** keys: we **still** implement **`create_deep_agent`** in **our FastAPI** (or a custom LangGraph app) and **per request** (or per user session) call **`init_chat_model`** (or equivalent) with credentials loaded from our **encrypted store**, and pass **runtime `context`** / tools as in [Context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering). The stock **`.env`‑only** deploy is a **complementary** option, not a substitute for BYOK. |
| **Checkpointers (self‑hosted)** | The **Checkpointer integrations** table lists the **PostgreSQL** package as **`langgraph-checkpoint-postgres`** (repo `langgraph`). ([Checkpointer integrations](https://docs.langchain.com/oss/python/integrations/checkpointers/index)) | We pin this package for durable threads in **our** DB; wire `PostgresSaver` (or the current API for that package) in `create_deep_agent(..., checkpointer=...)`. |
| **Agent Server (LangSmith / hosted)** | When using the **Agent Server**, persistence is **handled automatically** — you do **not** need to hand-wire a checkpointer the same way as a bare `compile()`. ([LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)) | If we use **LangSmith Deployment** for the **graph** only, checkpointing is **platform-managed**; if we use **self-hosted FastAPI**, we **must** supply a checkpointer. |
| **Client ↔ deployment** | Remote use: **`langgraph-sdk`** e.g. `get_client(url=..., headers={"Authorization": "Bearer ..."})` against the deployment URL ([Deploy with the CLI](https://docs.langchain.com/oss/python/deepagents/deploy#authentication)) | Next.js (or a BFF) can call a **remote** graph this way; auth header aligns with **Clerk/Supabase** JWT if we use managed deploy. **Elena’s** own API may instead **embed** the graph in-process. |
| **Streaming** | LangGraph implements streaming for step/token updates ([Python streaming](https://docs.langchain.com/oss/python/langgraph/streaming)); LangSmith also documents a **Streaming API** for the hosted stack ([LangSmith streaming](https://docs.langchain.com/langsmith/streaming)) | Expose **SSE** or **SDK streams** to the web client; same patterns whether hosted or self-hosted. |
| **Observability** | [Trace Deep Agents applications](https://docs.langchain.com/langsmith/trace-deep-agents) | Keep **LangSmith** optional; scrub secrets in traces. |

**Decision (unchanged, clarified):** **Primary path = self-hosted FastAPI + in-process `create_deep_agent` + `langgraph-checkpoint-postgres` + BYOK injection.** Optionally add **LangSmith** tracing and, later, evaluate **`deepagents deploy`** for a **subset** of traffic or for **sandbox-only** workloads if the beta fits product needs.

---

## 5. Data storage

| Concern | Choice | Notes |
|--------|--------|--------|
| **Primary DB** | **PostgreSQL** 15+ | Bases, variants, documents, users, **encrypted key metadata**, job status. |
| **Managed options** | **Neon**, **Supabase (Postgres)**, **AWS RDS**, **Cloud SQL** | **Neon** / **Supabase** are strong for v1; branching for dev is a plus (Neon). |
| **LangGraph state** | **Self-hosted:** package **`langgraph-checkpoint-postgres`** ([Checkpointer integrations](https://docs.langchain.com/oss/python/integrations/checkpointers/index)) wired into `create_deep_agent(..., checkpointer=...)`; **or** use **Agent Server** / **LangSmith Deployment** where the server manages persistence for you ([LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)). | Same Postgres **cluster** as the app is fine (separate schema/DB role); threads align with **VERSIONING_MODEL** (one thread per editing context). |
| **Blob / file storage** | **S3-compatible**: **Cloudflare R2**, **AWS S3**, **MinIO** (self-host) | PDFs, uploads, compile artifacts, optional JD uploads. **Presigned URLs** for client download. |
| **Cache & rate limits** | **Redis** (e.g. **Upstash Redis** serverless) | Per-user **compile** and **LLM proxy** throttles; optional **session** cache. |

**Resume JSON:** Store as **jsonb** in `resume_document` rows or **normalized tables**; v1 can be **jsonb** + Pydantic validation against **TEMPLATE_CONTRACT** schema for speed.

---

## 6. Authentication and authorization

| Layer | Choice | Rationale |
|------|--------|-----------|
| **Auth (B2C)** | **Clerk** **or** **Auth0** **or** **Supabase Auth** | **Clerk** + Next.js is very fast. **Supabase** bundles Auth + Postgres if you want one vendor. |
| **Sessions / JWT** | As provided by the IdP; API validates **JWT** (JWKS) per request | FastAPI + middleware for Clerk/Auth0 JWT. |
| **Row-level** | `user_id` on all base resumes, variants, documents, files | **Never** return another user’s data; add tests. |

**BYOK and auth:** Only the **authenticated user** can read/write their **own** key material (see §8).

---

## 7. Observability and product analytics

| Concern | Choice | Notes |
|--------|--------|--------|
| **Traces & LLM** | **LangSmith** (optional) | [Trace Deep Agents](https://docs.langchain.com/langsmith/trace-deep-agents) — **redact** prompts and tool outputs that could include secrets. |
| **Errors** | **Sentry** (frontend + backend) | |
| **Logs** | Structured JSON to **Axiom** / **Datadog** / **CloudWatch** (pick one) | **Never** log raw API keys or full decrypted key fields. |
| **Metrics** | **Prometheus** + Grafana **or** hosted **Datadog** | Compile success rate, p95 agent duration. |

---

## 8. BYOK (security model)

| Concern | Choice / practice |
|--------|---------------------|
| **Input** | User pastes or submits provider key in **settings** (HTTPS only); optional **one-time** “test connection” with a **minimal** model call. |
| **At rest** | **Encrypt** with **AES-256 (GCM)** in app, using a **KMS or env master key** (`ENCRYPTION_KEY` from KMS in prod). **Per-user** salt or per-row IV stored alongside ciphertext. **Do not** use reversible encoding without KMS for production long-term. |
| **In use** | Decrypt in **request/worker memory only**; pass to `init_chat_model` / client constructor; **clear** references after use where feasible. |
| **Rotation** | User can replace key; old ciphertext deleted. |
| **Model allowlist (optional)** | Constrain to providers you test (OpenAI, Anthropic, Google, etc.) to reduce footguns. |
| **Audit** | Log **key id** and **last_used_at**, not key body. |

**Provider-specific:** Support **OpenAI** (API key + optional org), **Anthropic**, **Google AI Studio**; document env vars the **user** sets only in the product UI, not in server `.env` (server `.env` only for **app** secrets such as `DATABASE_URL`, `ENCRYPTION_KEY`).

**Future:** “Org key vault” or **user-owned cloud KMS** is out of v1 unless you have paying enterprise.

---

## 9. Monorepo and delivery

**Repo paths (this repository):** `apps/web` (Next.js), `services/api` (Python `elena` package), `skills/` (Deep Agent skills), `infra/` (Compose + Docker).

| Concern | Choice | Notes |
|--------|--------|--------|
| **Layout** | **pnpm** **or** **uv**-centric Python + pnpm (split) | e.g. `apps/web` (Next), `services/api` (FastAPI), `packages/types` (optional). |
| **Python deps** | **uv** (recommended) or **poetry** | Reproducible lockfiles. |
| **CI** | **GitHub Actions**: lint, typecheck, tests, `docker build` for LaTeX image | On PR to `main`. |
| **IaC** (later) | **Terraform** or **Pulumi** | After product-market fit. |
| **Secrets in prod** | Platform **secrets manager** (Doppler, 1Password, AWS Secrets Manager) | **Never** commit. |

---

## 10. Testing (minimum for deploy confidence)

| Layer | Practice |
|------|----------|
| **API** | **pytest** + **httpx** `AsyncClient`; test authz and **409** on base delete with variants. |
| **Template** | Golden **JSON → LaTeX → PDF** in CI (already planned in product checkpoints). |
| **Agent** | **eval** sets with mock tools + optional recorded LangSmith runs; avoid flaky live LLM in default CI. |
| **E2E** | **Playwright** (optional) for import → editor smoke on staging. |

---

## 11. What we are **not** choosing for v1

- **Django** for API (heavier, less natural fit for long-lived SSE + LangGraph than FastAPI for a greenfield).
- **Ruby / Rails** (same reason).
- **In-browser LaTeX** as source of truth (WASM is possible for preview, but **source of truth** remains server-side compile for consistency).
- **Storing** user API keys in **localStorage** in plaintext (if any client cache, use short-lived server-issued session only, not the raw key).
- Relying on **only** the stock **`deepagents deploy` + `.env` provider keys** to satisfy end-user **BYOK** (must inject user keys in **our** API; see §4.1).

---

## 12. Summary table

| Area | Stack |
|------|--------|
| **Web** | TypeScript, Next.js (or Vite+React), Tailwind, shadcn/ui, TanStack Query |
| **API** | Python 3.12, FastAPI, Pydantic, SQLAlchemy/SQLModel, Alembic |
| **Agents** | `deepagents`, `LangGraph`, **`langgraph-checkpoint-postgres`** (if self-hosting state); optional **LiteLLM**; optional **`langgraph-sdk`** for a remote graph |
| **DB** | PostgreSQL (app data +, if self-hosted, LangGraph checkpoints with clear separation) |
| **Files** | S3-compatible (R2/S3) + presigned URLs |
| **Cache / queue** | Redis (Upstash or managed) |
| **Auth** | Clerk, Auth0, or Supabase Auth (JWT) — same providers supported by [Deep Agents deploy `auth` block](https://docs.langchain.com/oss/python/deepagents/deploy#auth) if we add managed graph later |
| **LaTeX** | Docker (TeX Live) + resource limits, optional queue (distinct from **execution sandboxes** in `deepagents deploy` docs: Modal, Daytona, etc.) |
| **BYOK** | AES-256 (or KMS) at rest, decrypt in worker only, never log |
| **Observability** | Sentry, **LangSmith** ([trace Deep Agents](https://docs.langchain.com/langsmith/trace-deep-agents)), structured logs |
| **Hosting** | Vercel/CF (front) + Fly/Railway/Render/Cloud Run (API + worker) |

---

## 13. Document control

| Version | Date | Notes |
|---------|------|--------|
| 0.1 | 2026-04-30 | Initial stack decision (BYOK, Python agent API, Next/Vite) |
| 0.2 | 2026-04-30 | LangChain docs alignment: §4.1 (deploy, checkpointer package, BYOK vs `.env`, streaming, trace links); `langgraph-checkpoint-postgres` naming; typo fix |
| 0.3 | 2026-04-30 | §9: explicit repo paths (`apps/web`, `services/api`, `skills/`, `infra/`) |

**Change log**

- 2026-04-30: v0.1
- 2026-04-30: v0.2 — reviewed against [LangChain docs](https://docs.langchain.com) (Deep Agents deploy, LangGraph persistence / checkpointers, streaming, trace)
- 2026-04-30: v0.3 — §9 repo layout paths for this repository
