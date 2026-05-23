"""Build full ``resume.tex`` from a validated ResumeDocument."""

from __future__ import annotations

from pathlib import Path

from elena.rendering.latex_escape import latex_escape_plain, latex_url_for_href
from elena.schemas.resume_document import ResumeDocument

_TEX_DIR = Path(__file__).resolve().parent / "tex_assets"


def _preamble_tex() -> str:
    return (_TEX_DIR / "preamble.tex").read_text(encoding="utf-8")


def resume_document_to_tex(document: ResumeDocument) -> str:
    """Produce a complete compilable ``.tex`` file (deterministic whitespace)."""

    body = build_body_tex(document)
    return f"{_preamble_tex()}\n{body}\\end{{document}}\n"


def build_body_tex(document: ResumeDocument) -> str:
    chunks: list[str] = []

    h = document.heading
    name = latex_escape_plain(h.full_name)

    heading_lines = [rf"{{\Huge \scshape {name} }} \\"]
    if h.address_line:
        heading_lines.append(rf"{latex_escape_plain(h.address_line)} \\ \vspace{{1pt}}")
    extras: list[str] = []

    def add_extra(block: str) -> None:
        extras.append(block)

    if h.phone:
        add_extra(rf"\small \raisebox{{-0.1\height}}\faPhone\ {latex_escape_plain(h.phone)}")
    if h.email:
        addr = latex_escape_plain(h.email)
        add_extra(
            rf"\href{{mailto:{addr}}}{{"
            rf"\raisebox{{-0.2\height}}\faEnvelope\ "
            rf"\underline{{{addr}}}}}",
        )
    if h.linkedin_url is not None:
        u = str(h.linkedin_url)
        add_extra(
            rf"\href{{{latex_url_for_href(u)}}}{{"
            rf"\raisebox{{-0.2\height}}\faLinkedin\ "
            rf"\underline{{{latex_escape_plain(u)}}}}}",
        )
    if h.github_url is not None:
        u = str(h.github_url)
        add_extra(
            rf"\href{{{latex_url_for_href(u)}}}{{"
            rf"\raisebox{{-0.2\height}}\faGithub\ "
            rf"\underline{{{latex_escape_plain(u)}}}}}",
        )
    joined_extras = " ~ ".join(extras)
    chunks.append("\\begin{center}\n")
    chunks.append("\n ".join(heading_lines) + "\n")
    if joined_extras:
        chunks.append(joined_extras + "\n")
    chunks.append("\\vspace{-8pt}\n\\end{center}\n\n")

    # Education
    if document.education:
        chunks.append("\\section{Education}\n\\resumeSubHeadingListStart\n")
        for edu in document.education:
            chunks.append(
                "    \\resumeSubheading\n"
                f"      {{{latex_escape_plain(edu.institution)}}}"
                f"{{{latex_escape_plain(edu.date_range)}}}"
                f"{{{latex_escape_plain(edu.degree)}}}"
                f"{{{latex_escape_plain(edu.location)}}}\n",
            )
        chunks.append("  \\resumeSubHeadingListEnd\n\n")

    # Coursework
    rc = document.relevant_coursework
    if rc is not None and rc.courses:
        chunks.append("\\section{Relevant Coursework}\n\\begin{multicols}{4}\n")
        chunks.append("\\begin{itemize}[itemsep=-5pt, parsep=3pt]\n")
        for course in rc.courses:
            chunks.append(f"    \\item\\small {latex_escape_plain(course)}\n")
        chunks.append(r"\end{itemize}" + "\n\\end{multicols}\n")
        chunks.append(r"\vspace*{2.0\multicolsep}" + "\n\n")

    # Experience
    if document.experience:
        chunks.append("\\section{Experience}\n\\resumeSubHeadingListStart\n\n")
        for exp in document.experience:
            chunks.append(
                "    \\resumeSubheading\n"
                f"      {{{latex_escape_plain(exp.organization)}}}"
                f"{{{latex_escape_plain(exp.date_range)}}}"
                f"{{{latex_escape_plain(exp.title)}}}"
                f"{{{latex_escape_plain(exp.location)}}}\n",
            )
            if exp.bullets:
                chunks.append("      \\resumeItemListStart\n")
                for b in exp.bullets:
                    chunks.append(f"        \\resumeItem{{{latex_escape_plain(b)}}}\n")
                chunks.append("      \\resumeItemListEnd\n")
        chunks.append("\\resumeSubHeadingListEnd\n\\vspace{-16pt}\n\n")

    # Projects
    if document.projects:
        chunks.append("\\section{Projects}\n\\vspace{-5pt}\n\\resumeSubHeadingListStart\n")
        for proj in document.projects:
            tech = latex_escape_plain(proj.tech_stack or "")
            pname = latex_escape_plain(proj.name)
            pdate = latex_escape_plain(proj.date or "")
            heading_left = rf"\textbf{{{pname}}} $|$ \emph{{{tech}}}"
            chunks.append(f"\\resumeProjectHeading\n{{{heading_left}}}{{{pdate}}}\n")
            if proj.bullets:
                chunks.append("\\resumeItemListStart\n")
                for b in proj.bullets:
                    chunks.append(f"  \\resumeItem{{{latex_escape_plain(b)}}}\n")
                chunks.append("\\resumeItemListEnd\n\\vspace{-13pt}\n")
        chunks.append("\\resumeSubHeadingListEnd\n\\vspace{-15pt}\n\n")

    # Skills
    ts = document.technical_skills
    lang = (ts.languages or "").strip() if ts else ""
    dev_tools = (ts.developer_tools or "").strip() if ts else ""
    tech_fw = (ts.technologies_frameworks or "").strip() if ts else ""
    if lang or dev_tools or tech_fw:
        chunks.append("\\section{Technical Skills}\n\\begin{itemize}[leftmargin=0.15in, label={}]\n")
        chunks.append("    \\small{\\item{\n")
        if lang:
            esc = latex_escape_plain(lang)
            chunks.append(rf"     \textbf{{Languages}}{{:{esc}}} \\" + "\n")
        if dev_tools:
            esc = latex_escape_plain(dev_tools)
            chunks.append(rf"     \textbf{{Developer Tools}}{{:{esc}}} \\" + "\n")
        if tech_fw:
            esc = latex_escape_plain(tech_fw)
            chunks.append(rf"     \textbf{{Technologies/Frameworks}}{{:{esc}}} \\" + "\n")
        chunks.append(r"    }}" + "\n \\end{itemize}\n \\vspace{-16pt}\n\n")

    # Leadership / extracurricular
    if document.leadership_extracurricular:
        chunks.append(
            "\\section{Leadership / Extracurricular}\n\\resumeSubHeadingListStart\n",
        )
        for exp in document.leadership_extracurricular:
            chunks.append(
                "        \\resumeSubheading"
                f"{{{latex_escape_plain(exp.organization)}}}"
                f"{{{latex_escape_plain(exp.date_range)}}}"
                f"{{{latex_escape_plain(exp.title)}}}"
                f"{{{latex_escape_plain(exp.location)}}}\n",
            )
            if exp.bullets:
                chunks.append("            \\resumeItemListStart\n")
                for b in exp.bullets:
                    chunks.append(f"                \\resumeItem{{{latex_escape_plain(b)}}}\n")
                chunks.append("            \\resumeItemListEnd\n")
        chunks.append("\\resumeSubHeadingListEnd\n")

    return "".join(chunks)
