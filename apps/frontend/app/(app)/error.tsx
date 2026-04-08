"use client";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-2/60 p-8 text-center">
      <h2 className="text-xl font-semibold">Dashboard error</h2>
      <p className="mt-2 text-sm text-muted">{error.message}</p>
      <button
        onClick={() => reset()}
        className="mt-4 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black"
      >
        Retry
      </button>
    </div>
  );
}
