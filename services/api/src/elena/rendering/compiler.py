"""Run pdflatex in a sandboxed temp dir and collect logs."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompileResult:
    ok: bool
    pdf_bytes: bytes | None
    log_tail: str
    page_count: int | None


def _tail(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return "[...truncated]\n" + text[-max_chars:]


def _detect_page_count(pdf_path: Path) -> int | None:
    try:
        scan = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return None
    if scan.returncode != 0:
        return None
    for line in scan.stdout.splitlines():
        if line.startswith("Pages:"):
            chunk = line.split(":", maxsplit=1)[-1].strip()
            try:
                return int(chunk)
            except ValueError:
                return None
    return None


async def compile_resume_tex(tex_source: str, *, timeout_seconds: float) -> CompileResult:
    """Write ``resume.tex`` and invoke ``pdflatex`` twice (-interaction=nonstopmode).

    Blocking work runs in ``asyncio.to_thread`` so the event loop stays responsive.
    """

    def _blocking() -> CompileResult:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="elena-compile-") as td:
            tdir = Path(td)
            tex_file = tdir / "resume.tex"
            tex_file.write_text(tex_source, encoding="utf-8")

            cmds = []
            stderr_all: list[str] = []

            cmd = (
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_file.relative_to(tdir)),
            )
            for _ in range(2):
                result = subprocess.run(
                    cmd,
                    cwd=str(tdir),
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                stderr_all.append(result.stdout + "\n" + result.stderr)
                cmds.append(str(result.returncode))

            pdf_path = tdir / "resume.pdf"
            merged = "\n".join(stderr_all)

            if not pdf_path.is_file():
                return CompileResult(False, None, _tail(merged), None)

            pdf_bytes = pdf_path.read_bytes()
            magic_ok = pdf_bytes.startswith(b"%PDF")
            pc = _detect_page_count(pdf_path)

            tail = _tail(merged)
            if not magic_ok:
                return CompileResult(False, pdf_bytes, tail + "\npdf_magic_invalid", pc)
            cmd_ok = all(c == "0" for c in cmds)
            return CompileResult(cmd_ok, pdf_bytes, tail, pc)

    return await asyncio.to_thread(_blocking)
