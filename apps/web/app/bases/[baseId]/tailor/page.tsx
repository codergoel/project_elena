'use client';

import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useState } from 'react';

export default function TailorForkPage({ params }: { params: { baseId: string } }) {
  const baseId = params.baseId;
  const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

  const [userId, setUserId] = useState('');
  useEffect(() => {
    try {
      const v = sessionStorage.getItem('elena:dev-user-id');
      if (v) setUserId(v);
    } catch {
      /* ignore */
    }
  }, []);

  const hdr = useCallback(() => ({ 'x-user-id': userId }), [userId]);

  const [title, setTitle] = useState<string | null>(null);
  const [label, setLabel] = useState('');
  const [jd, setJd] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [forkResult, setForkResult] = useState<{
    variantId: string;
    jdUrl: string | null;
  } | null>(null);

  useEffect(() => {
    void (async () => {
      if (!userId) return;
      setErr(null);
      try {
        const br = await fetch(`${apiBase}/api/v1/bases/${baseId}`, { headers: hdr() });
        const jb = await br.json().catch(() => ({}));
        if (!br.ok) throw new Error(JSON.stringify(jb));
        if (typeof jb.title === 'string') setTitle(jb.title);
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, [apiBase, baseId, hdr, userId]);

  const onFork = async (e: FormEvent) => {
    e.preventDefault();
    if (!userId) return;
    setBusy(true);
    setErr(null);
    setForkResult(null);
    try {
      const body: { label?: string; jd_plaintext?: string } = {};
      const lab = label.trim();
      if (lab) body.label = lab;
      const jt = jd.trim();
      if (jt) body.jd_plaintext = jt;

      const r = await fetch(`${apiBase}/api/v1/bases/${baseId}/variants`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...hdr() },
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(JSON.stringify(j));
      const vid = typeof j.variant?.id === 'string' ? (j.variant.id as string) : null;
      if (!vid) throw new Error('missing variant.id in fork response');
      const jdUrl = typeof j.jd_download_url === 'string' ? (j.jd_download_url as string) : null;
      setForkResult({ variantId: vid, jdUrl });
    } catch (ec) {
      setErr(String(ec));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col gap-6 p-6 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-50">
      <header>
        <p className="text-xs uppercase tracking-wide text-neutral-500">Phase 8 · tailor fork</p>
        <h1 className="text-xl font-semibold">{title ?? 'Fork for a job posting'}</h1>
        <p className="mt-1 font-mono text-xs text-neutral-500">base {baseId}</p>
      </header>

      <nav className="flex flex-wrap gap-3 text-sm">
        <Link href={`/editor/base/${baseId}`} className="underline">
          Back to editor
        </Link>
        <Link href="/" className="underline">
          Home
        </Link>
      </nav>

      <label className="text-[11px] text-neutral-500">
        Dev <code>X-User-Id</code>
        <input
          className="mt-1 w-full rounded border px-2 py-1 font-mono dark:border-neutral-600"
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
        />
      </label>

      <form className="flex flex-col gap-4" onSubmit={(ev) => void onFork(ev)}>
        <div>
          <label className="text-sm font-medium">Variant label (optional)</label>
          <input
            className="mt-1 w-full rounded border px-3 py-2 dark:border-neutral-600"
            value={label}
            onChange={(ev) => setLabel(ev.target.value)}
            placeholder="e.g. Acme staff engineer"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Job description (optional, stored privately)</label>
          <textarea
            className="mt-1 w-full rounded border px-3 py-2 dark:border-neutral-600"
            rows={8}
            value={jd}
            onChange={(ev) => setJd(ev.target.value)}
            placeholder="Paste the posting…"
          />
        </div>
        <button
          type="submit"
          disabled={busy || !userId}
          className="rounded bg-neutral-900 px-4 py-2 text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
        >
          Fork variant
        </button>
      </form>

      {forkResult ? (
        <section className="rounded border border-neutral-200 p-4 text-sm dark:border-neutral-700">
          <p className="font-medium">Created variant</p>
          <p className="mt-1 font-mono text-xs break-all">{forkResult.variantId}</p>
          {forkResult.jdUrl ? (
            <p className="mt-2">
              JD download URL (expires):{' '}
              <a className="break-all underline" href={forkResult.jdUrl} target="_blank" rel="noreferrer">
                {forkResult.jdUrl}
              </a>
            </p>
          ) : (
            <p className="mt-2 text-neutral-600 dark:text-neutral-400">No JD blob (paste text to get a link).</p>
          )}
          <p className="mt-3 text-neutral-600 dark:text-neutral-400">
            Compile: <code>POST /api/v1/variants/{'{id}'}/render</code> · Thread:{' '}
            <code>POST /api/v1/variants/{'{id}'}/thread</code>
          </p>
        </section>
      ) : null}

      {err ? (
        <pre className="whitespace-pre-wrap rounded border border-red-400 bg-red-50 p-3 text-xs text-red-900 dark:bg-red-950 dark:text-red-100">
          {err}
        </pre>
      ) : null}
    </div>
  );
}
