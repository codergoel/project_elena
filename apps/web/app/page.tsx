export default function Home() {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Project Elena</h1>
      <p className="max-w-md text-center text-sm text-neutral-600 dark:text-neutral-400">
        Next.js app (checkpoint 1.2). Configure{" "}
        <code className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-xs dark:bg-neutral-800">
          NEXT_PUBLIC_API_URL
        </code>{" "}
        to point at the API (default{" "}
        <code className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-xs dark:bg-neutral-800">
          {apiUrl}
        </code>
        ).
      </p>
      <p className="flex flex-wrap gap-2">
        <a
          href="/import"
          className="rounded bg-neutral-900 px-3 py-1.5 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900"
        >
          Import résumé
        </a>
        <a
          href="/guided"
          className="rounded border border-neutral-400 px-3 py-1.5 text-sm dark:border-neutral-500"
        >
          Guided résumé
        </a>
      </p>
    </main>
  );
}
