



## Execution sequencing

Finish **Phase 8 → Phase 11** (JD/variants UX, reliability, observability, deploy) **before** investing in heavier **BYOK** polish for: **Phase 7.4** (SSE streaming), **5.2** optional non-Gemini providers, **7.5** (LLM recs), **8.2** web research, **10.1** LangSmith-era tracing.

What already works **with ``GEMINI_API_KEY``:** heuristic PDF import, LLM import preview, guided FSM, compile/render spine, editor shell, **Phase 7.3** Gemini LangGraph agent (tools + Postgres checkpoints), Phase 8.1 variant fork + JD.

---

| Phase/Checkpoint | Task Description | Status |
| ----- | ----- | ----- |
| **Phase 0 — Product and scope lock** |  | ☐ Done |
| 0.1 | One-pager: Problem, primary user, non-goals, success metrics. | ☐ Done |
| 0.2 | Template contract: Fixed Jake-style template; supported sections/fields; "unsupported → profile only" rule. | ☐ Done |
| 0.3 | Versioning model: User → Base resume(s) → Variant(s); UI naming; "fork" vs "edit in place" definition. | ☐ Done |
| **Phase 1 — Foundation (repo, env, CI)** |  | ☐ Done |
| 1.1 | Monorepo layout: web/, api/, agent/, skills/, infra/. | ☐ Done |
| 1.2 | Local dev: Docker Compose (or equivalent) for API, DB; .env.example; README "clone to running app." | ☐ Done |
| 1.3 | CI: Lint, typecheck, tests on PR; no secrets in repo. | ☐ Done |
| **Phase 2 — Data model and persistence** |  | ☐ Pending |
| 2.1 | Schema v1: ResumeDocument (JSON) \+ UserProfile validated. | ☐ Pending |
| 2.2 | DB migrations: Users, sessions, base\_resume, resume\_document, variant, thread\_id mapping. | ☐ Pending |
| 2.3 | Blob storage: Uploads (PDF), generated PDFs; retention and signed URLs. | ☐ Pending |
| **Phase 3 — Render and compile (spine)** |  | ☐ Pending |
| 3.1 | JSON → LaTeX: Deterministic render from ResumeDocument to .tex. | ☐ Pending |
| 3.2 | Sandbox compile: pdflatex/latexmk in container; timeouts, log capture, page count signal. | ☐ Pending |
| 3.3 | API contract: POST /resumes/:id/render returns PDF URL \+ metadata. | ☐ Pending |
| 3.4 | Golden tests: 2–3 fixture JSONs → expected PDF builds in CI to catch template regressions. | ☐ Pending |
| **Phase 4 — Auth and API surface** |  | ☐ Pending |
| 4.1 | Auth: Sign-up/login (or OAuth); session/JWT; user\_id on all resources. | ☐ Pending |
| 4.2 | CRUD for bases and variants: Create/list/open base; fork variant; delete with confirmation. | ☐ Pending |
| 4.3 | Rate limits and quotas: Per user: uploads, LLM calls, compiles (even if coarse in v1). | ☐ Pending |
| **Phase 5 — Import path (PDF → base)** |  | ☐ Pending |
| 5.1 | Extraction: Text extraction path working; optional vision path scoped as "later" or stubbed. | ☐ Mostly in repo |
| 5.2 | Map extract → structured JSON (**heuristic ✓** in repo); **LLM**/vision mapping uses **Gemini** when ``GEMINI_API_KEY`` set, else optional OpenAI-compatible API — **Configurable** via env. | Partial |
| 5.3 | Import UI: Upload → review (incl. low-confidence cues) → "Create base" → **opens Phase 7** editor link from `/import` (`/editor/base/{id}`). | Wired (web link) |
| **Phase 6 — Guided “from scratch” path** |  | ☐ Pending |
| 6.1 | Slot model: ordered slots (heading → education → experience → skills) + ``guided_checkpoint`` JSON (skips); API + deterministic FSM in ``elena/guided_fsm.py``. | Scaffold in repo |
| 6.2 | Conversational intake: **Deferred** until API keys (**agent** replaces REST-only shell). | Deferred (BYOK) |
| 6.3 | Live preview: debounced POST ``/bases/{id}/render`` from `/guided/[baseId]` wizard. | Scaffold in repo |
| **Phase 7 — Shared editor (viewer \+ chat)** |  | ☐ Pending |
| 7.1 | Editor shell: **`/editor/base/[id]`** — stacked mobile / split desktop; compiled PDF iframe + stub chat sidebar; **wired** import + guided exits. | Scaffold in repo |
| 7.2 | Threading: ``conversation_threads`` for **bases** and **variants** — ``GET``/``POST`` ``/bases/{id}/thread`` and ``/variants/{id}/thread`` stub ``langgraph_thread_id`` (see VERSIONING_MODEL). | Mostly in repo |
| 7.3 | Deep agent: **Gemini** + LangGraph ReAct; tools ``get_resume_json`` / ``put_resume_json`` / ``render_resume_pdf``; Postgres checkpoints via ``langgraph-checkpoint-postgres``; ``POST …/agent/turn`` (base + variant). | Mostly in repo |
| 7.4 | Streaming SSE/WebSocket tokens + "PDF updated" events. | **Deferred** (after 7.3 non-stream turn) |
| 7.5 | Recommendations cards post-compile (typically **LLM**). Heuristic-only recs may land earlier without keys. | **Deferred** (keys); optional heuristic |
| **Phase 8 — JD variants and research** | Next focus ahead of LangGraph/agent. | Priority |
| 8.1 | Variant fork: clone ``ResumeDocument``; optional ``jd_plaintext`` → private JD blob + signed download URL; ``PUT /variants/{id}/document``; signed download uses ``text/plain`` for ``.txt``; web **Tailor** at ``/bases/[baseId]/tailor``. | Mostly in repo |
| 8.2 | Research tools: Web search (**LLM/agent** tooling); subagent for isolated context. | **Deferred** (keys/runtime) unless stub without search |
| 8.3 | JD alignment loop: Recs → user message → **agent patch** → compile → compare to base. | **Deferred** with 7.3; carve non-agent UX before keys |
| **Phase 9 — Reliability, safety, compliance** | Scaffold in repo | ☐ Pending (polish backlog) |
| 9.1 | Prompt and tool safety: No fabrication of employers/degrees; refusal patterns; PII handling in logs. | Light system prompt steer in agent graph; broader policy + logging scrub TBD |
| 9.2 | Compile failure UX: User-visible errors from LaTeX log; agent skill path for "fix compile." | Render API + agent tool expose ``latex_user_hint`` from compile log (``latex_hints`` helper); web UX polish TBD |
| 9.3 | Backup and restore: Document versions recoverable; export JSON + PDF per base/variant. | ``GET /api/v1/bases/{id}/export`` and ``GET /api/v1/variants/{id}/export`` return envelope JSON + metadata; full version history / bundled PDF restore TBD |
| 9.4 | Privacy: Data retention policy; delete account flow; where PDFs live. | ``docs/PRIVACY_AND_DATA.md`` tables; automated delete-account still backlog |
| **Phase 10 — Observability and ops** | Metrics + alerting guidance | Scaffold in repo |
| 10.1 | Tracing: LangSmith (**or equivalent**) for agent + compile spans; trace IDs in support tools. | ``X-Request-ID`` + structured ``elena.access`` logs + ``docs/OBSERVABILITY.md`` correlation notes; LangSmith **Deferred** (keys). |
| 10.2 | Metrics: Compile success rate, latency, LLM cost per session, error rates. | Prometheus ``prometheus-client`` metrics (HTTP histograms/counters; LaTeX compile; quotas; agent + import LLM counters); gated ``GET /metrics``. |
| 10.3 | Alerting: Compile service down, LLM quota, DB errors. | ``docs/OBSERVABILITY.md`` sample PromQL/rules; infra scrape + paging still backlog |
| **Phase 11 — Staging and production deploy** |  | ☐ Pending |
| 11.1 | Staging: Parity with prod; **scaled-down LLM** optional. | LLM parity **Deferred** until keys |
| 11.2 | IaC: Terraform/Pulumi/K8s manifests; DB backups, migrations job. | ☐ Pending |
| 11.3 | Production checklist: HTTPS, CORS, CSP, dependency audit, Sentry, runbooks. | ☐ Pending |
| 11.4 | Launch: Feature flags; rollback plan; minimal docs/FAQ. | ☐ Pending |

