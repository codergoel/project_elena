'use client';

import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

type Msg = { id: string; role: 'user' | 'assistant'; body: string };

export default function BaseEditorPage({ params }: { params: { baseId: string } }) {
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
  const [threadIdDisplay, setThreadIdDisplay] = useState<string | null>(null);
  const [lgThread, setLgThread] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [messages, setMessages] = useState<Msg[]>([
    {
      id: 'sys-1',
      role: 'assistant',
      body:
        'Gemini LangGraph agent (Phase 7.3): ask for edits or a summary of your résumé. Requires the API GEMINI_API_KEY and Postgres checkpoints.',
    },
  ]);

  const loadAll = useCallback(async () => {
    if (!userId) return;
    setErr(null);
    try {
      const br = await fetch(`${apiBase}/api/v1/bases/${baseId}`, { headers: hdr() });
      const jb = await br.json().catch(() => ({}));
      if (!br.ok) throw new Error(JSON.stringify(jb));
      if (typeof jb.title === 'string') setTitle(jb.title);

      let tr = await fetch(`${apiBase}/api/v1/bases/${baseId}/thread`, { headers: hdr() });
      if (tr.status === 404) {
        tr = await fetch(`${apiBase}/api/v1/bases/${baseId}/thread`, {
          method: 'POST',
          headers: hdr(),
        });
      }
      const tj = await tr.json().catch(() => ({}));
      if (!tr.ok) throw new Error(JSON.stringify(tj));
      if (typeof tj.id === 'string') setThreadIdDisplay(tj.id as string);
      if (typeof tj.langgraph_thread_id === 'string') setLgThread(tj.langgraph_thread_id as string);
    } catch (e) {
      setErr(String(e));
    }
  }, [apiBase, baseId, hdr, userId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const refreshPdf = async () => {
    if (!userId) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${apiBase}/api/v1/bases/${baseId}/render`, {
        method: 'POST',
        headers: hdr(),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(JSON.stringify(j));
      if (typeof (j as { pdf_url?: string }).pdf_url === 'string') {
        setPdfUrl((j as { pdf_url: string }).pdf_url);
      }
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!userId) return;
    const t = window.setTimeout(refreshPdf, 400);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial compile only after userId
  }, [userId, baseId]);

  const [draft, setDraft] = useState('');

  const onChat = async (e: FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || !userId) return;
    const uid = crypto.randomUUID();
    setDraft('');
    setMessages((prev) => [...prev, { id: uid, role: 'user', body: text }]);
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${apiBase}/api/v1/bases/${baseId}/agent/turn`, {
        method: 'POST',
        headers: { ...hdr(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(JSON.stringify(j));
      const reply = typeof (j as { assistant?: string }).assistant === 'string'
        ? (j as { assistant: string }).assistant
        : JSON.stringify(j);
      setMessages((prev) => [...prev, { id: `a-${uid}`, role: 'assistant', body: reply }]);
      const u = (j as { last_pdf_url?: unknown }).last_pdf_url;
      if (typeof u === 'string' && u.startsWith('http')) setPdfUrl(u);
    } catch (e) {
      setErr(String(e));
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${uid}`,
          role: 'assistant',
          body:
            'Request failed — is the API running with ``GEMINI_API_KEY`` and reachable Postgres?',
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const subtitle = useMemo(() => title ?? '(loading title…)', [title]);

  return (
    <div className="flex min-h-screen flex-col bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-50">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wide text-neutral-500">Phase 7.1 shell</p>
          <h1 className="truncate text-lg font-semibold">{subtitle}</h1>
          <p className="truncate font-mono text-[11px] text-neutral-500">base {baseId}</p>
        </div>
        <nav className="flex flex-wrap items-center gap-2 text-sm">
          <button
            type="button"
            disabled={busy || !userId}
            onClick={() => void refreshPdf()}
            className="rounded border border-neutral-400 px-3 py-1.5 disabled:opacity-50 dark:border-neutral-600"
          >
            Compile PDF
          </button>
          <Link href="/" className="underline">
            Home
          </Link>
          <Link href="/import" className="underline">
            Import
          </Link>
          <Link href="/guided" className="underline">
            Guided
          </Link>
          <Link href={`/bases/${baseId}/tailor`} className="underline">
            Tailor
          </Link>
        </nav>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row lg:divide-x lg:divide-neutral-200 lg:dark:divide-neutral-800">
        <section className="flex min-h-[45vh] flex-1 flex-col p-4 lg:min-h-0 lg:w-1/2">
          <h2 className="mb-2 text-sm font-medium text-neutral-600 dark:text-neutral-400">Résumé PDF</h2>
          {pdfUrl ? (
            <iframe title="Compiled résumé" src={pdfUrl} className="min-h-[60vh] w-full flex-1 rounded border lg:min-h-0" />
          ) : (
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Compile to view output (needs TeX toolchain on the API).
            </p>
          )}
          {lgThread ? (
            <p className="mt-2 truncate font-mono text-[11px] text-neutral-500" title={lgThread}>
              Thread stub: {lgThread}
              {threadIdDisplay ? ` (row ${threadIdDisplay})` : ''}
            </p>
          ) : null}
        </section>

        <section className="flex min-h-[40vh] flex-1 flex-col border-t border-neutral-200 p-4 dark:border-neutral-800 lg:border-t-0 lg:w-1/2">
          <h2 className="mb-2 text-sm font-medium text-neutral-600 dark:text-neutral-400">Chat (stub)</h2>

          <label className="mb-3 text-[11px] text-neutral-500">
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

          <ul className="mb-4 flex flex-1 flex-col gap-2 overflow-y-auto rounded border border-neutral-200 bg-white p-2 dark:border-neutral-800 dark:bg-neutral-900">
            {messages.map((m) => (
              <li
                key={m.id}
                className={`max-w-[95%] rounded px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'ml-auto bg-neutral-200 dark:bg-neutral-800'
                    : 'mr-auto bg-neutral-100 dark:bg-neutral-800/70'
                }`}
              >
                <span className="text-[10px] font-semibold uppercase text-neutral-500">{m.role}</span>
                <p className="whitespace-pre-wrap">{m.body}</p>
              </li>
            ))}
          </ul>

          <form onSubmit={onChat} className="flex flex-col gap-2">
            <textarea
              rows={3}
              value={draft}
              onChange={(ev) => setDraft(ev.target.value)}
              placeholder="Type a draft message…"
              className="rounded border px-3 py-2 dark:border-neutral-600"
            />
            <button
              type="submit"
              disabled={busy || !userId}
              className="w-fit rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
            >
              Send to agent
            </button>
          </form>

          {err ? (
            <p className="mt-4 rounded border border-red-400 bg-red-50 p-2 text-sm text-red-900 dark:bg-red-950 dark:text-red-100">
              {err}
            </p>
          ) : null}
        </section>
      </div>
    </div>
  );
}
