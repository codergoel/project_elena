'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';

function hdr(userId: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'x-user-id': userId,
  };
}

export default function GuidedStartPage() {
  const router = useRouter();
  const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
    /\/$/,
    '',
  );
  const [userId, setUserId] = useState('');
  useEffect(() => {
    try {
      const key = 'elena:dev-user-id';
      const saved = sessionStorage.getItem(key);
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
  const [title, setTitle] = useState('My résumé');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onStart(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!userId || userId.length < 30) {
      setErr('Provide a UUID for X-User-Id.');
      return;
    }
    setBusy(true);
    try {
      const cr = await fetch(`${apiBase}/api/v1/bases`, {
        method: 'POST',
        headers: hdr(userId),
        body: JSON.stringify({ title, source: 'guided' }),
      });
      const jb = await cr.json().catch(() => ({}));
      if (!cr.ok) throw new Error(JSON.stringify(jb));

      const id = jb.id as string;
      const br = await fetch(`${apiBase}/api/v1/bases/${id}/guided/bootstrap`, {
        method: 'POST',
        headers: { 'x-user-id': userId },
      });
      const bj = await br.json().catch(() => ({}));
      if (!br.ok) throw new Error(JSON.stringify(bj));

      router.push(`/guided/${id}`);
    } catch (e0) {
      setErr(String(e0));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col gap-6 p-8">
      <h1 className="text-2xl font-semibold">Guided résumé (Phase 6)</h1>
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        Creates a <code className="font-mono text-xs">source=guided</code> base and runs the fixed
        slot flow (heading → education → experience → skills). LLM/agent chat deferred to Phase 7.
      </p>
      <label className="flex flex-col gap-1 text-sm">
        Dev <code>X-User-Id</code> (UUID)
        <input
          value={userId}
          onChange={(ev) => setUserId(ev.target.value.trim())}
          className="rounded border px-2 py-1 font-mono text-xs dark:border-neutral-600"
          spellCheck={false}
        />
      </label>
      <form className="flex flex-col gap-4" onSubmit={onStart}>
        <label className="flex flex-col gap-1 text-sm">
          Base title
          <input
            value={title}
            onChange={(ev) => setTitle(ev.target.value)}
            className="rounded border px-2 py-1 dark:border-neutral-600"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
        >
          Start wizard
        </button>
      </form>
      {err ? (
        <p className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-50">
          {err}
        </p>
      ) : null}
      <p>
        <a href="/" className="text-sm underline">
          ← Home
        </a>
      </p>
    </main>
  );
}
