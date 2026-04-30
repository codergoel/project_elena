# Product one-pager — AI LaTeX Resume Editor

**Checkpoint:** 0.1 (scope lock)  
**Working name:** Elena (or replace with final product name)  
**Last updated:** 2026-04-30

---

## Problem

Students and early-career candidates maintain **LaTeX résumés** (often Jake’s Anonymous style) for a clean, formal look. They repeatedly hit the same friction:

- **One-page constraint** forces endless rephrasing, shortening, and layout checks.
- **Micro-layout issues** (e.g. a bullet that breaks awkwardly across lines) trigger a slow loop: identify → rewrite in ChatGPT → paste into LaTeX → compile → repeat.
- **Multiple contexts** (different roles, companies, JDs) multiply versions and prep time.

There is no single place that combines **structured LaTeX output**, **live preview**, and an **expert-like assistant** that edits the real source of truth—not a disconnected text blob.

---

## Primary user

**Main persona:** Undergraduate or graduate student (or early-career professional) who already uses or is willing to use **LaTeX/Jake-style** résumés and cares about **one page**, **consistency**, and **speed** when tailoring for jobs.

**Secondary:** Career services or peer reviewers (later; not v1 scope).

---

## Solution (one sentence)

A web platform where users **import a PDF** or **build from scratch in a guided chat**, land on a **split view** (live one-page **Jake-template PDF** + **chat and recommendations**), then optionally create **JD-specific variants** with research-backed alignment suggestions—powered by a **Deep Agents** harness, **structured résumé data**, and **Agent Skills** for domain workflows.

---

## Core value


| For the user        | What we deliver                                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------ |
| Less repetition     | Chat-driven edits that update the real template-backed résumé and preview.                                   |
| One-page discipline | Explicit layout/page signals and recommendations, not guesswork.                                             |
| JD alignment        | Variants under a **base** résumé, with optional company/JD context and rephrase suggestions.                 |
| Fidelity            | **Structured canonical model** → fixed LaTeX template; overflow content preserved in a **profile superset**. |


---

## Non-goals (v1)

- **Arbitrary free-form LaTeX editing** by users (no full TeX IDE); template-bound fields only unless explicitly expanded later.
- **Guaranteed factual verification** of employers, dates, or claims; the product assists drafting—the user remains accountable.
- **Recruiter ATS “score”** as a primary metric unless defined and validated separately.
- **Multi-template marketplace** in v1; one **fixed Jake-style** template and schema.
- **Offline-first** or native mobile apps.
- **Fully automated job applications** or auto-submit to job boards.

---

## Success metrics (v1 and near-term)

**Activation**

- % of signups who reach a **compiled base PDF** (import or guided) within one session.
- Time from **start onboarding** → **first successful preview** (median).

**Engagement**

- **Chat turns per session** and % of sessions with at least one **accepted recommendation** or applied edit.
- **Variants created per base** (distribution; not only average).

**Quality**

- **Compile success rate** after agent edits (target: high nineties after stabilisation).
- **User-reported “good enough to send”** (simple in-app thumbs or post-session survey).

**Business / ops (when relevant)**

- **Cost per successful session** (LLM + compile + storage), tracked per feature (import vs guided vs JD).

---

## Scope boundaries (decisions to keep explicit)

1. **Truth layer:** Canonical data is **structured JSON (or equivalent)** mapped to the template; PDF upload is **input**, not the long-term source of truth.
2. **Overflow:** Content that does not map to the template is stored in a **user profile / extraction superset**, not dropped silently.
3. **Versioning:** **Multiple bases** per user; **multiple JD variants** per base; UI copy must distinguish **base** vs **variant**.

---

## Related documents

- **[TEMPLATE_CONTRACT.md](./TEMPLATE_CONTRACT.md)** — Checkpoint **0.2**: fields and sections supported by the locked Jake-style LaTeX template (`main.tex`) and the **profile overflow** rule.
- **[VERSIONING_MODEL.md](./VERSIONING_MODEL.md)** — Checkpoint **0.3**: user → base → variant hierarchy, fork vs edit-in-place, UI naming, persistence hints.
- **[TECH_STACK.md](./TECH_STACK.md)** — Deployable **web** stack and **BYOK** (bring your own API key) model.

---

## Risks (acknowledged, not solved on this page)

- LLM **hallucination** on mapping from messy PDFs → strong validation and review steps.
- **Web research** for JD mode: accuracy, stale pages, and cost → citations policy and fallbacks.
- **LaTeX sandbox** security and cost at scale.

---

## Document control


| Version | Author  | Notes                            |
| ------- | ------- | -------------------------------- |
| 0.1     | Product | Initial checkpoint 0.1 one-pager |


When scope changes, bump the table and add a one-line **Change log** below.

**Change log**

- 2026-04-30: Initial version.
- 2026-04-30: Linked `TEMPLATE_CONTRACT.md` (checkpoint 0.2).
- 2026-04-30: Linked `VERSIONING_MODEL.md` (checkpoint 0.3).

