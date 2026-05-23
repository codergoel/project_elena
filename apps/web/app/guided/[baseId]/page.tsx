'use client';

import Link from 'next/link';
import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

type GuidedStatus = {
  bootstrap_required: boolean;
  terminal: boolean;
  next_slot: string | null;
  prompt: string | null;
  checkpoint: { skipped_slots: string[] };
  resume: unknown;
};

export default function GuidedWizardPage({ params }: { params: { baseId: string } }) {
  const { baseId } = params;
  const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
    /\/$/,
    '',
  );

  const [userId, setUserId] = useState('');
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('elena:dev-user-id');
      if (saved) setUserId(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const hdr = useCallback(() => ({ 'x-user-id': userId }), [userId]);

  const [status, setStatus] = useState<GuidedStatus | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const docFingerprint = useMemo(
    () => (status?.resume ? JSON.stringify(status.resume) : ''),
    [status?.resume],
  );

  const fetchStatus = useCallback(async () => {
    const r = await fetch(`${apiBase}/api/v1/bases/${baseId}/guided/status`, {
      headers: hdr(),
    });
    const j = (await r.json().catch(() => ({}))) as GuidedStatus;
    if (!r.ok) throw new Error(JSON.stringify(j));
    let next = j;
    if (j.bootstrap_required) {
      const b = await fetch(`${apiBase}/api/v1/bases/${baseId}/guided/bootstrap`, {
        method: 'POST',
        headers: hdr(),
      });
      const bj = await b.json().catch(() => ({}));
      if (!b.ok) throw new Error(JSON.stringify(bj));
      const r2 = await fetch(`${apiBase}/api/v1/bases/${baseId}/guided/status`, {
        headers: hdr(),
      });
      next = (await r2.json().catch(() => ({}))) as GuidedStatus;
      if (!r2.ok) throw new Error(JSON.stringify(next));
    }
    setStatus(next);
    return next;
  }, [apiBase, baseId, hdr]);

  useEffect(() => {
    if (!userId) return;
    void (async () => {
      try {
        await fetchStatus();
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, [userId, fetchStatus]);

  useEffect(() => {
    if (!userId || !docFingerprint || status?.bootstrap_required || !status?.resume) return;

    const t = window.setTimeout(async () => {
      try {
        const r = await fetch(`${apiBase}/api/v1/bases/${baseId}/render`, {
          method: 'POST',
          headers: hdr(),
        });
        const j = (await r.json().catch(() => ({}))) as { pdf_url?: string };
        if (r.ok && typeof j.pdf_url === 'string') setPdfUrl(j.pdf_url);
      } catch {
        /* compile may fail in minimal dev setups */
      }
    }, 700);
    return () => window.clearTimeout(t);
  }, [apiBase, baseId, docFingerprint, hdr, status?.bootstrap_required, status?.resume, userId]);

  const [heading, setHeading] = useState({
    full_name: '',
    email: '',
    phone: '',
    address_line: '',
  });
  const [edu, setEdu] = useState({
    institution: '',
    degree: '',
    date_range: '',
    location: '',
  });
  const [xp, setXp] = useState({
    organization: '',
    title: '',
    date_range: '',
    location: '',
    bullets: '',
  });
  const [langs, setLangs] = useState('Python, SQL, Docker');

  async function postStep(path: string, body: object) {
    setErr(null);
    setBusy(true);
    try {
      const r = await fetch(`${apiBase}/api/v1/bases/${baseId}/guided/step/${path}`, {
        method: 'POST',
        headers: { ...hdr(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(JSON.stringify(j));
      await fetchStatus();
    } catch (e0) {
      setErr(String(e0));
    } finally {
      setBusy(false);
    }
  }

  async function onHeading(e: FormEvent) {
    e.preventDefault();
    await postStep('heading', {
      full_name: heading.full_name,
      email: heading.email.trim() || null,
      phone: heading.phone.trim() || null,
      address_line: heading.address_line.trim() || null,
    });
  }

  async function onEducation(skip: boolean) {
    if (skip) {
      await postStep('education', { skip: true });
      return;
    }
    await postStep('education', {
      skip: false,
      entry: {
        institution: edu.institution,
        degree: edu.degree,
        date_range: edu.date_range,
        location: edu.location,
      },
    });
  }

  async function onExperience(skip: boolean) {
    if (skip) {
      await postStep('experience', { skip: true });
      return;
    }
    const bullets = xp.bullets.split(/\n/).map((s) => s.trim()).filter(Boolean);
    await postStep('experience', {
      skip: false,
      entry: {
        organization: xp.organization,
        title: xp.title,
        date_range: xp.date_range,
        location: xp.location,
        bullets,
      },
    });
  }

  async function onSkills(skip: boolean) {
    if (skip) await postStep('skills', { skip: true });
    else await postStep('skills', { skip: false, languages: langs });
  }

  const effectiveSlot = status?.terminal ? null : (status?.next_slot ?? null);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-8">
      <div className="flex flex-wrap justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Guided wizard</h1>
          <p className="text-xs text-neutral-500">Base {baseId}</p>
        </div>
        <Link href="/guided" className="text-sm underline">
          New session
        </Link>
        <Link href="/" className="text-sm underline">
          Home
        </Link>
      </div>

      <label className="text-xs font-mono text-neutral-500">
        Dev user UUID
        <input
          className="ml-2 w-72 rounded border px-2 py-0.5 dark:border-neutral-600"
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

      <div className="grid gap-6 lg:grid-cols-[1fr,minmax(240px,1fr)]">
        <section className="flex flex-col gap-4">
          {status && (status.checkpoint.skipped_slots ?? []).length > 0 ? (
            <p className="text-xs text-neutral-500">
              Skipped: {status.checkpoint.skipped_slots.join(', ')}
            </p>
          ) : null}

          {status?.prompt ? (
            <div className="rounded bg-neutral-100 p-3 text-sm dark:bg-neutral-900">{status.prompt}</div>
          ) : null}

          {effectiveSlot === 'heading' ? (
            <form className="flex flex-col gap-2" onSubmit={onHeading}>
              <input
                required
                placeholder="Full legal name"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={heading.full_name}
                onChange={(ev) => setHeading((h) => ({ ...h, full_name: ev.target.value }))}
              />
              <input
                placeholder="Email (optional)"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={heading.email}
                onChange={(ev) => setHeading((h) => ({ ...h, email: ev.target.value }))}
              />
              <input
                placeholder="Phone (optional)"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={heading.phone}
                onChange={(ev) => setHeading((h) => ({ ...h, phone: ev.target.value }))}
              />
              <button
                type="submit"
                disabled={busy}
                className="mt-2 w-fit rounded bg-neutral-900 px-3 py-1.5 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900"
              >
                Save heading
              </button>
            </form>
          ) : null}

          {effectiveSlot === 'education' ? (
            <div className="flex flex-col gap-2">
              <input
                placeholder="School"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={edu.institution}
                onChange={(ev) => setEdu({ ...edu, institution: ev.target.value })}
              />
              <input
                placeholder="Degree"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={edu.degree}
                onChange={(ev) => setEdu({ ...edu, degree: ev.target.value })}
              />
              <input
                placeholder="Dates"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={edu.date_range}
                onChange={(ev) => setEdu({ ...edu, date_range: ev.target.value })}
              />
              <input
                placeholder="City, State"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={edu.location}
                onChange={(ev) => setEdu({ ...edu, location: ev.target.value })}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onEducation(true)}
                  className="rounded border px-3 py-1 text-sm dark:border-neutral-500"
                >
                  Skip
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onEducation(false)}
                  className="rounded bg-emerald-800 px-3 py-1 text-sm text-white dark:bg-emerald-600"
                >
                  Save education
                </button>
              </div>
            </div>
          ) : null}

          {effectiveSlot === 'experience' ? (
            <div className="flex flex-col gap-2">
              <input
                placeholder="Company"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={xp.organization}
                onChange={(ev) => setXp({ ...xp, organization: ev.target.value })}
              />
              <input
                placeholder="Title"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={xp.title}
                onChange={(ev) => setXp({ ...xp, title: ev.target.value })}
              />
              <input
                placeholder="Dates"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={xp.date_range}
                onChange={(ev) => setXp({ ...xp, date_range: ev.target.value })}
              />
              <input
                placeholder="Location"
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={xp.location}
                onChange={(ev) => setXp({ ...xp, location: ev.target.value })}
              />
              <textarea
                placeholder="Bullets — one line each"
                rows={5}
                className="rounded border px-2 py-1 font-mono text-xs dark:border-neutral-600"
                value={xp.bullets}
                onChange={(ev) => setXp({ ...xp, bullets: ev.target.value })}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onExperience(true)}
                  className="rounded border px-3 py-1 text-sm dark:border-neutral-500"
                >
                  Skip
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onExperience(false)}
                  className="rounded bg-emerald-800 px-3 py-1 text-sm text-white dark:bg-emerald-600"
                >
                  Save experience
                </button>
              </div>
            </div>
          ) : null}

          {effectiveSlot === 'skills' ? (
            <div className="flex flex-col gap-2">
              <textarea
                rows={3}
                className="rounded border px-2 py-1 dark:border-neutral-600"
                value={langs}
                onChange={(ev) => setLangs(ev.target.value)}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onSkills(true)}
                  className="rounded border px-3 py-1 text-sm dark:border-neutral-500"
                >
                  Skip skills
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onSkills(false)}
                  className="rounded bg-emerald-800 px-3 py-1 text-sm text-white dark:bg-emerald-600"
                >
                  Save skills line
                </button>
              </div>
            </div>
          ) : null}

          {status?.terminal ? (
            <div className="rounded border border-green-700 bg-green-50 p-3 text-sm dark:border-green-600 dark:bg-green-950 dark:text-green-100">
              <p className="mb-3">
                Guided skeleton finished. Tune the structured JSON anytime via{' '}
                <code className="text-xs">PUT /api/v1/bases/{baseId}/document</code>.
              </p>
              <Link
                href={`/editor/base/${baseId}`}
                className="inline-block rounded bg-violet-800 px-3 py-2 text-xs text-white dark:bg-violet-600"
              >
                Open Phase 7 editor shell
              </Link>
            </div>
          ) : null}

          {err ? (
            <p className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-900 dark:border-red-700 dark:bg-red-950 dark:text-red-100">
              {err}
            </p>
          ) : null}
        </section>

        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Live preview (~700ms)</h2>
          {pdfUrl ? (
            <iframe title="Résumé PDF" src={pdfUrl} className="h-[620px] w-full rounded border" />
          ) : (
            <p className="text-xs text-neutral-500">PDF appears after compile completes.</p>
          )}
        </section>
      </div>
    </main>
  );
}
