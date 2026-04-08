export default function AppLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-64 animate-pulse rounded bg-surface-2/60" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-40 animate-pulse rounded-xl bg-surface-2/60" />
        <div className="h-40 animate-pulse rounded-xl bg-surface-2/60" />
      </div>
      <div className="h-64 animate-pulse rounded-xl bg-surface-2/60" />
    </div>
  );
}
