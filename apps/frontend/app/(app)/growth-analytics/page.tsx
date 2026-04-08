"use client";

import { useQuery } from "@tanstack/react-query";
import { growthApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function GrowthAnalyticsPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["growth-metrics"],
    queryFn: growthApi.metrics,
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (isError) {
    return <div className="text-red-400">{(error as Error)?.message}</div>;
  }

  return (
    <div className="space-y-6">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Growth Analytics</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">New Users</p>
            <p className="mt-2 text-2xl font-semibold">{data?.new_users ?? 0}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Agent Runs</p>
            <p className="mt-2 text-2xl font-semibold">{data?.agent_runs ?? 0}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Referrals</p>
            <p className="mt-2 text-2xl font-semibold">{data?.referrals ?? 0}</p>
          </div>
          <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Window</p>
            <p className="mt-2 text-2xl font-semibold">{data?.window_days ?? 7}d</p>
          </div>
        </CardContent>
      </Card>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Most Shared Agents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {data?.most_shared_agents?.length ? (
            data.most_shared_agents.map((agent: any) => (
              <div key={agent.agent_id} className="flex items-center justify-between rounded-lg border border-border/60 bg-surface-2/60 p-3">
                <span>{agent.agent_name}</span>
                <span className="text-xs text-muted">{agent.count} shares</span>
              </div>
            ))
          ) : (
            <div className="text-muted">No share data yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
