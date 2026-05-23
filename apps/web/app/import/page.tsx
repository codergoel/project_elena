'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';

function defaultHeaders(userId: string): HeadersInit {
  return {
    'x-user-id': userId,
  };
}

export default function ImportPage() {
  const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
    /\/$/,
    '',
  );

  const [userId, setUserId] = useState('');
  useEffect(() => {
    try {
      const key = 'elena:dev-user-id';
      const saved = typeof window !== 'undefined' ? sessionStorage.getItem(key) : null;
      if (saved) {
        setUserId(saved);
        return;
      }
      const nid = crypto.randomUUID();
      sessionStorage.setItem(key, nid);
      setUserId(nid);
    } catch {
      setUserId('');
    }
  }, []);

  const [title, setTitle] = useState('Imported résumé');
  const [file, setFile] = useState<File | null>(null);
  const [pdfKey, setPdfKey] = useState<string | null>(null);
  const [uploadLog, setUploadLog] = useState<string>('');

  type Jsonish = Record<string, unknown>;

  const [resumeEnvelope, setResumeEnvelope] = useState<Jsonish | null>(null);
  const [profileSnapshot, setProfileSnapshot] = useState<Jsonish>({
    overflow_sections: [],
    extensions: {},
  });
  const [confidences, setConfidences] = useState<Record<string, number> | null>(
    null,
  );

  const [commitResult, setCommitResult] = useState<object | string | null>(null);
  const [committedBaseId, setCommittedBaseId] = useState<string | null>(null);
  const [pdfHref, setPdfHref] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canAct = Boolean(userId && userId.length > 10);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    setCommitResult(null);
    setCommittedBaseId(null);
    setPdfHref(null);
    if (!canAct || !file) {
      setError('Choose a PDF and ensure dev user UUID is set.');
      setBusy(false);
      return;
    }
    const fd = new FormData();
    fd.append('file', file);

    try {
      const res = await fetch(`${apiBase}/api/v1/import/pdf`, {
        method: 'POST',
        headers: defaultHeaders(userId),
        body: fd,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(JSON.stringify(body) || res.statusText);
        setBusy(false);
        return;
      }
      const pk = typeof body.pdf_key === 'string' ? body.pdf_key : null;
      setPdfKey(pk);
      const trunc = Boolean(body.truncated);
      const pages =
        typeof body.page_count === 'number' ? String(body.page_count) : '?';
      setUploadLog(
        `Stored PDF key ${pk ?? '(missing)'} — ${pages} page(s), truncated=${String(trunc)}, chars=${String(body.extracted_chars)}`,
      );
      const extracted =
        typeof body.extracted_text === 'string' ? body.extracted_text : '';
      await onHeuristic(pk, extracted);
    } finally {
      setBusy(false);
    }
  }

  async function onHeuristic(key: string | null, extractedText?: string) {
    setError(null);
    const payload =
      extractedText !== undefined && extractedText.length > 0
        ? { extracted_text: extractedText }
        : key
          ? { pdf_key: key }
          : {};
    try {
      const res = await fetch(`${apiBase}/api/v1/import/preview/heuristic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...defaultHeaders(userId) },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(JSON.stringify(body) || res.statusText);
        return;
      }
      const envelope =
        typeof body.resume === 'object' && body.resume !== null
          ? (body.resume as Jsonish)
          : null;
      setResumeEnvelope(envelope);
      if (typeof body.user_profile === 'object' && body.user_profile !== null) {
        setProfileSnapshot(body.user_profile as Jsonish);
      } else {
        setProfileSnapshot({ overflow_sections: [], extensions: {} });
      }
      const fc =
        typeof body.field_confidence === 'object' && body.field_confidence !== null
          ? (body.field_confidence as Record<string, number>)
          : null;
      setConfidences(fc);
    } catch (err) {
      setError(String(err));
    }
  }

  async function onLlmPreview() {
    setError(null);
    if (!pdfKey || !canAct) {
      setError('Upload a PDF first (LLM path uses blob re-read unless you paste text separately).');
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${apiBase}/api/v1/import/preview/llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...defaultHeaders(userId) },
        body: JSON.stringify({ pdf_key: pdfKey }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(JSON.stringify(body) || res.statusText);
        return;
      }
      const envelope =
        typeof body.resume === 'object' && body.resume !== null
          ? (body.resume as Jsonish)
          : null;
      setResumeEnvelope(envelope);
      if (typeof body.user_profile === 'object' && body.user_profile !== null) {
        setProfileSnapshot(body.user_profile as Jsonish);
      }
      const fc =
        typeof body.field_confidence === 'object' && body.field_confidence !== null
          ? (body.field_confidence as Record<string, number>)
          : null;
      setConfidences(fc);
    } finally {
      setBusy(false);
    }
  }

  async function onCommit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCommitResult(null);
    setCommittedBaseId(null);
    setPdfHref(null);
    if (!resumeEnvelope || !canAct) {
      setError('Run heuristic (or LLM) preview before committing.');
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${apiBase}/api/v1/import/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...defaultHeaders(userId) },
        body: JSON.stringify({
          title,
          envelope: resumeEnvelope,
          user_profile: profileSnapshot,
          ...(pdfKey ? { pdf_key: pdfKey } : {}),
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(JSON.stringify(body) || res.statusText);
        return;
      }
      setCommitResult(body);
      const bid =
        typeof body.base_resume === 'object' &&
        body.base_resume !== null &&
        typeof (body.base_resume as { id?: unknown }).id === 'string'
          ? String((body.base_resume as { id: string }).id)
          : null;
      setCommittedBaseId(bid);
      if (typeof body.source_pdf_download_url === 'string') {
        setPdfHref(body.source_pdf_download_url);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Import résumé (PDF)</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Phase 5.3 scaffold: upload, heuristic preview, optional LLM preview, commit base with
            optional signed PDF URL.
          </p>
        </div>
        <Link
          href="/"
          className="text-sm text-neutral-700 underline underline-offset-2 dark:text-neutral-300"
        >
          ← Home
        </Link>
      </div>

      <label className="flex flex-col gap-2 text-sm">
        <span>Dev auth: X-User-Id (persisted)</span>
        <input
          className="rounded border border-neutral-300 px-2 py-1 font-mono text-xs dark:border-neutral-600"
          value={userId}
          onChange={(ev) => {
            const v = ev.target.value;
            setUserId(v);
            try {
              sessionStorage.setItem('elena:dev-user-id', v);
            } catch {
              /* ignore */
            }
          }}
          placeholder="UUID"
          spellCheck={false}
        />
      </label>

      <form className="flex flex-col gap-4 rounded border border-neutral-200 p-4 dark:border-neutral-700" onSubmit={onUpload}>
        <h2 className="text-lg font-medium">1. Upload PDF</h2>
        <input
          type="file"
          accept="application/pdf"
          onChange={(ev) => setFile(ev.target.files?.[0] ?? null)}
        />
        <button
          type="submit"
          disabled={busy || !canAct}
          className="w-fit rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
        >
          Upload &amp; heuristic map
        </button>
      </form>

      {uploadLog ? <p className="text-xs font-mono text-neutral-700 dark:text-neutral-300">{uploadLog}</p> : null}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => pdfKey && onHeuristic(pdfKey)}
          disabled={busy || !canAct || !pdfKey}
          className="rounded border border-neutral-400 px-3 py-2 text-xs disabled:opacity-50 dark:border-neutral-500"
        >
          Re-run heuristic (from blob key)
        </button>
        <button
          type="button"
          onClick={onLlmPreview}
          disabled={busy || !canAct || !pdfKey}
          className="rounded border border-neutral-400 px-3 py-2 text-xs disabled:opacity-50 dark:border-neutral-500"
        >
          LLM preview (requires API keys server-side)
        </button>
      </div>

      {resumeEnvelope ? (
        <section className="flex flex-col gap-2 rounded border border-neutral-200 p-4 dark:border-neutral-700">
          <h2 className="text-lg font-medium">2. Preview payload</h2>
          <pre className="max-h-80 overflow-auto rounded bg-neutral-100 p-2 text-xs dark:bg-neutral-900">
            {JSON.stringify(resumeEnvelope, null, 2)}
          </pre>
          <details className="text-xs">
            <summary className="cursor-pointer">User profile snapshot (overflow)</summary>
            <pre className="mt-2 max-h-48 overflow-auto rounded bg-neutral-50 p-2 dark:bg-neutral-900">
              {JSON.stringify(profileSnapshot, null, 2)}
            </pre>
          </details>
          {confidences ? (
            <pre className="max-h-40 overflow-auto rounded bg-neutral-50 p-2 text-xs dark:bg-neutral-900">
              field_confidence:{'\n'}
              {JSON.stringify(confidences, null, 2)}
            </pre>
          ) : null}
        </section>
      ) : null}

      <form className="flex flex-col gap-4 rounded border border-neutral-200 p-4 dark:border-neutral-700" onSubmit={onCommit}>
        <h2 className="text-lg font-medium">3. Create base résumé</h2>
        <label className="flex flex-col gap-2 text-sm">
          Title
          <input
            className="rounded border border-neutral-300 px-2 py-1 dark:border-neutral-600"
            value={title}
            onChange={(ev) => setTitle(ev.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={busy || !canAct || !resumeEnvelope}
          className="w-fit rounded bg-emerald-800 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-emerald-600"
        >
          Commit base
        </button>
      </form>

      {pdfHref ? (
        <section className="flex flex-col gap-2 rounded border border-neutral-200 p-4 dark:border-neutral-700">
          <h3 className="font-medium">Source PDF (signed)</h3>
          <a className="text-sm underline" href={pdfHref} target="_blank" rel="noreferrer">
            Open PDF
          </a>
          <iframe title="Imported PDF preview" src={pdfHref} className="h-[480px] w-full rounded border" />
        </section>
      ) : null}

      {committedBaseId ? (
        <p>
          <Link
            href={`/editor/base/${committedBaseId}`}
            className="rounded bg-violet-800 px-3 py-2 text-sm text-white dark:bg-violet-600"
          >
            Open Phase 7 editor (PDF + chat stub)
          </Link>
        </p>
      ) : null}

      {commitResult ? (
        <pre className="max-h-96 overflow-auto rounded bg-neutral-100 p-2 text-xs dark:bg-neutral-900">
          commit:{'\n'}
          {JSON.stringify(commitResult, null, 2)}
        </pre>
      ) : null}

      {error ? (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
          {error}
        </p>
      ) : null}
    </main>
  );
}
