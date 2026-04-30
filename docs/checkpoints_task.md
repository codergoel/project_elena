

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
| 5.1 | Extraction: Text extraction path working; optional vision path scoped as "later" or stubbed. | ☐ Pending |
| 5.2 | Mapping LLM \+ validation: Map extract → ResumeDocument \+ overflow → UserProfile; confidence flags for user review. | ☐ Pending |
| 5.3 | Import UI: Upload → review screen for low-confidence fields → "Create base" → lands on editor with PDF. | ☐ Pending |
| **Phase 6 — Guided “from scratch” path** |  | ☐ Pending |
| 6.1 | Slot model: Required fields derived from template; state for what’s missing. | ☐ Pending |
| 6.2 | Conversational intake: Agent or hybrid FSM+LLM asks next question; handles clarifications. | ☐ Pending |
| 6.3 | Live preview: Debounced re-render as slots commit; same editor shell as import path. | ☐ Pending |
| **Phase 7 — Shared editor (viewer \+ chat)** |  | ☐ Pending |
| 7.1 | Editor shell: Left PDF viewer; right chat; responsive basics. | ☐ Pending |
| 7.2 | Threading: One LangGraph thread (or equivalent) per base (or per session—decide and document). | ☐ Pending |
| 7.3 | Deep Agent wired: create\_deep\_agent with tools: read/write resume.json, render, compile; skills=\[...\], checkpointer. | ☐ Pending |
| 7.4 | Streaming: SSE/WebSocket: tokens \+ "PDF updated" events. | ☐ Pending |
| 7.5 | Recommendations: Post-compile analysis → cards; click → pre-filled prompt; telemetry (which recs used). | ☐ Pending |
| **Phase 8 — JD variants and research** |  | ☐ Pending |
| 8.1 | Variant fork: Clone ResumeDocument into variant with jd\_ref metadata. | ☐ Pending |
| 8.2 | Research tools: Web search (with citations or snippets policy); subagent for isolated context. | ☐ Pending |
| 8.3 | JD alignment loop: Recs → user message → agent patch → compile → compare to base. | ☐ Pending |
| **Phase 9 — Reliability, safety, compliance** |  | ☐ Pending |
| 9.1 | Prompt and tool safety: No fabrication of employers/degrees; refusal patterns; PII handling in logs. | ☐ Pending |
| 9.2 | Compile failure UX: User-visible errors from LaTeX log; agent skill path for "fix compile." | ☐ Pending |
| 9.3 | Backup and restore: Document versions recoverable; export JSON \+ PDF per base/variant. | ☐ Pending |
| 9.4 | Privacy: Data retention policy; delete account flow; where PDFs live. | ☐ Pending |
| **Phase 10 — Observability and ops** |  | ☐ Pending |
| 10.1 | Tracing: LangSmith (or equivalent) for agent \+ compile spans; trace IDs in support tools. | ☐ Pending |
| 10.2 | Metrics: Compile success rate, latency, LLM cost per session, error rates. | ☐ Pending |
| 10.3 | Alerting: Compile service down, LLM quota, DB errors. | ☐ Pending |
| **Phase 11 — Staging and production deploy** |  | ☐ Pending |
| 11.1 | Staging: Parity with prod: secrets manager, real sandbox, scaled-down LLM. | ☐ Pending |
| 11.2 | IaC: Terraform/Pulumi/K8s manifests; DB backups, migrations job. | ☐ Pending |
| 11.3 | Production checklist: HTTPS, CORS, CSP, dependency audit, Sentry, runbooks. | ☐ Pending |
| 11.4 | Launch: Feature flags; rollback plan; minimal docs/FAQ. | ☐ Pending |

