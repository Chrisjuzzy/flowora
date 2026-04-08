export default function LoadingFounderMode() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-64 animate-pulse rounded bg-surface-2/60" />
      <div className="grid gap-4 lg:grid-cols-[1.1fr_2fr]">
        <div className="h-80 animate-pulse rounded-xl bg-surface-2/60" />
        <div className="h-80 animate-pulse rounded-xl bg-surface-2/60" />
      </div>
    </div>
  );
}
