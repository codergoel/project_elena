# Template contract — Checkpoint 0.2

**Status:** Locked for v1 (derived from repo template)  
**Canonical LaTeX source:** `[main.tex](./main.tex)`  
**Lineage:** Jake Gutierrez résumé style; MIT License; based on [sb2nov/resume](https://github.com/sb2nov/resume).

This document is the **single source of truth** for what the product may render into the live résumé. Anything else from uploads or chat stays in the **user profile / extraction superset** until the template contract is explicitly extended.

---

## 1. Locked template identity


| Property         | Value                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------- |
| Engine           | pdfLaTeX (typical); document uses `\pdfgentounicode=1`                                 |
| Document class   | `article`, `letterpaper`, `11pt`                                                       |
| Page target      | One page (layout margins and spacing are tuned for that)                               |
| Notable packages | `fullpage`, `titlesec`, `enumitem`, `hyperref`, `tabularx`, `fontawesome5`, `multicol` |
| External input   | `\input{glyphtounicode}` — build must provide this file on TeX path                    |


**v1 rule:** All generated résumés use this structure and section order unless a future version bumps this document’s version.

---

## 2. Section order (fixed for v1)

Order in PDF **must** match `main.tex`:

1. **Heading** (center block, not a `\section`)
2. **Education** — `\section{Education}`
3. **Relevant Coursework** — `\section{Relevant Coursework}`
4. **Experience** — `\section{Experience}`
5. **Projects** — `\section{Projects}`
6. **Technical Skills** — `\section{Technical Skills}`
7. **Leadership / Extracurricular** — `\section{Leadership / Extracurricular}`

**Section titles are fixed strings** in v1 (no user-renamed section headings in the LaTeX output).

---

## 3. Supported constructs and data fields

Each row is **in-template** for v1. Map app / JSON schema fields to these.

### 3.1 Heading (`\begin{center}` …)


| Logical field  | Required | LaTeX role                                              |
| -------------- | -------- | ------------------------------------------------------- |
| `full_name`    | Yes      | `\Huge \scshape …`                                      |
| `address_line` | No       | Single line under name                                  |
| `phone`        | No       | `\faPhone` line                                         |
| `email`        | No       | `\href{mailto:…}{\faEnvelope …}`                        |
| `linkedin_url` | No       | `\href{…}{\faLinkedin …}` (display text may mirror URL) |
| `github_url`   | No       | `\href{…}{\faGithub …}`                                 |


---

### 3.2 Education — list of **education entries**

Each entry uses `\resumeSubheading{•}{•}{•}{•}` inside `\resumeSubHeadingListStart` … `End`.


| Field         | Maps to `\resumeSubheading` arg | Notes                        |
| ------------- | ------------------------------- | ---------------------------- |
| `institution` | 1 (bold left)                   | School / university name     |
| `date_range`  | 2 (bold right)                  | e.g. `Sep. 2017 -- May 2021` |
| `degree`      | 3 (italic left)                 | Full degree line             |
| `location`    | 4 (italic right)                | City, State                  |


**Multiple degrees:** multiple entries in the list (each one `\resumeSubheading` block). No separate “sub-subheading” in the sample; `\resumeSubSubheading` exists in the preamble but is **not used** in the canonical body—use only if you extend this contract in a later version.

---

### 3.3 Relevant Coursework — **flat list of course names**


| Field     | Required                             | Notes            |
| --------- | ------------------------------------ | ---------------- |
| `courses` | No (section may be omitted or empty) | Array of strings |


**Layout:** Rendered inside `multicols` with **4 columns** (`\begin{multicols}{4}`), `\item\small …` per course, as in `main.tex`.

---

### 3.4 Experience — list of **experience entries**

Each entry: one `\resumeSubheading` + `\resumeItemListStart` … `\resumeItem` … `\resumeItemListEnd`.


| Field          | Maps to                   | Notes                          |
| -------------- | ------------------------- | ------------------------------ |
| `organization` | `\resumeSubheading` arg 1 | Company / org name             |
| `date_range`   | arg 2                     | Employment period              |
| `title`        | arg 3                     | Role title                     |
| `location`     | arg 4                     | City, State                    |
| `bullets`      | `\resumeItem{…}`          | Ordered list of bullet strings |


---

### 3.5 Projects — list of **project entries**

Each entry uses `\resumeProjectHeading` + item list.


| Field        | Required | Notes                       |
| ------------ | -------- | --------------------------- |
| `name`       | Yes      | Bold part of left cell      |
| `tech_stack` | No       | Shown after `$              |
| `date`       | No       | Right column (bold small)   |
| `bullets`    | No       | List of `\resumeItem` lines |


**LaTeX shape:** `\textbf{Name} $|$ \emph{tech}` on the left, date on the right (match sample lines 193–194).

---

### 3.6 Technical Skills — **three labeled lines** (single visual block)


| Field                     | Label in PDF                | Notes                         |
| ------------------------- | --------------------------- | ----------------------------- |
| `languages`               | **Languages**               | Prefix `Languages:` in output |
| `developer_tools`         | **Developer Tools**         |                               |
| `technologies_frameworks` | **Technologies/Frameworks** |                               |


All are optional; omit a line if empty. Structure matches `main.tex` lines 224–229 (single `\item` with `\\` breaks).

---

### 3.7 Leadership / Extracurricular — same shape as **Experience**

Same fields as §3.4: `organization`, `date_range`, `title`, `location`, `bullets` (reuse schema type or alias field names in JSON if you prefer `activity` over `organization`—generator must still emit the same LaTeX).

---

## 4. LaTeX macros reserved but not used in canonical body

Defined in `main.tex` but **not** illustrated in the current body. **Not part of v1 schema** unless you add them here in a future checkpoint:


| Macro                  | Purpose                                                   |
| ---------------------- | --------------------------------------------------------- |
| `\classesList`         | Four-part list item (legacy / alternate coursework style) |
| `\resumeSubSubheading` | Two-column sub-line under a subheading                    |
| `\resumeSubItem`       | Thin wrapper around `\resumeItem`                         |


---

## 5. Explicitly **not** in this template (v1)

The following are **out of contract** for the live Jake PDF unless you change `main.tex` and re-issue this document:

- Photo / headshot  
- Summary, objective, or “About” block  
- Publications, patents, certifications, awards (as their own sections)  
- Skills as tag cloud or star ratings  
- Arbitrary extra `\section{…}` titles  
- Multi-page layout, cover letter, or CV class  
- Custom colors beyond what the preamble already allows

**→ All such content** from PDF extraction or guided chat **must** go to **user profile / superset** (or future “promote to section” flow), **not** silently merged into LaTeX.

---

## 6. Overflow rule (profile superset)

1. **In contract:** Only fields and sections listed in §§2–3 may be written into the generator that produces this template’s PDF.
2. **Out of contract:** Any section or field present in a user upload or conversation that does not map to §§2–3 is stored in the **structured user profile** (extraction superset), with optional `unmapped_section_title` + `raw_text` or structured blobs.
3. **No silent drop:** The product may omit it from the PDF but **must not discard** it from persisted profile data during import.
4. **Promotion:** Adding a new supported section requires updating `**main.tex`**, the **JSON schema**, and **this contract** (new checkpoint 0.2 revision).

---

## 7. Implementation checklist (for engineering)

- JSON schema / Pydantic models match §§3.1–3.7 field names and cardinality.  
- Renderer emits sections in §2 order; empty sections omitted or rendered empty per product UX decision (document that choice).  
- CI golden build includes `glyphtounicode` on path.  
- Mapper LLM prompt references **this file** or a generated subset so it never invents new section types for v1.

---

## Document control


| Version | Date       | Notes                                                  |
| ------- | ---------- | ------------------------------------------------------ |
| 0.1     | 2026-04-30 | Initial contract from `docs/main.tex` (checkpoint 0.2) |


