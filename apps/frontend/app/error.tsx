"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-center text-white">
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold">Something went wrong</h1>
        <p className="text-sm text-slate-300">{error.message}</p>
        <button
          onClick={() => reset()}
          className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
