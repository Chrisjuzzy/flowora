"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type FounderRunSummary = {
  agents_created?: number;
  workflows_created?: number;
  listings_created?: number;
  ideas_used?: number;
  templates_created?: {
    agents?: number[];
    workflows?: number[];
    tools?: number[];
  };
};

type FounderRunItem = {
  id: number;
  run_type: string;
  status: string;
  summary?: FounderRunSummary;
  trend_snapshot?: any;
  created_at: string;
  error?: string | null;
};

type FounderRunDetail = FounderRunItem & {
  automation_ideas?: any[];
  agents_created?: any[];
  workflows_created?: any[];
  templates_published?: any;
  listings_published?: any[];
};

function TrendSparkline({ values }: { values: number[] }) {
  if (!values.length) {
    return <div className="text-xs text-muted">No trend data yet.</div>;
  }

  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = Math.max(max - min, 1);
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1 || 1)) * 160;
    const y = 40 - ((value - min) / span) * 30;
    return `${x},${y}`;
  });

  return (
    <svg viewBox="0 0 160 40" className="h-10 w-full">
      <polyline
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        points={points.join(" ")}
        className="text-cyan-300"
      />
    </svg>
  );
}

export default function FounderModePage() {
  const { data: runsData } = useQuery({
    queryKey: ["founder-runs"],
    queryFn: () => analyticsApi.founderRuns(20),
  });

  const runs: FounderRunItem[] = runsData?.runs || [];
  const [selectedId, setSelectedId] = useState<number | null>(runs[0]?.id ?? null);

  useEffect(() => {
    if (!selectedId && runs.length) {
      setSelectedId(runs[0].id);
    }
  }, [runs, selectedId]);

  const { data: runDetail } = useQuery<FounderRunDetail>({
    queryKey: ["founder-run", selectedId],
    queryFn: () => analyticsApi.founderRun(selectedId as number),
    enabled: Boolean(selectedId),
  });

  const trendSeries = useMemo(() => {
    const ordered = [...runs].reverse();
    return {
      agents: ordered.map((run) => run.summary?.agents_created ?? 0),
      workflows: ordered.map((run) => run.summary?.workflows_created ?? 0),
      listings: ordered.map((run) => run.summary?.listings_created ?? 0),
    };
  }, [runs]);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-muted">Founder Mode</p>
          <h1 className="text-3xl font-semibold heading-serif">Autonomous Growth Command</h1>
          <p className="text-sm text-muted">Weekly autonomous builds, trends, and marketplace launches.</p>
        </div>
        <Button variant="secondary">Run Founder Mode</Button>
      </div>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_2fr]">
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Run History</CardTitle>
            <CardDescription>Review weekly autonomous launch cycles.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {runs.map((run) => (
              <button
                key={run.id}
                onClick={() => setSelectedId(run.id)}
                className={`w-full rounded-lg border px-4 py-3 text-left transition ${
                  selectedId === run.id
                    ? "border-cyan-400/60 bg-cyan-500/10 text-white"
                    : "border-border/60 bg-surface-2/50 text-muted hover:border-cyan-400/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">Run #{run.id}</span>
                  <Badge variant="outline">{run.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted">{new Date(run.created_at).toLocaleString()}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  <span>Agents {run.summary?.agents_created ?? 0}</span>
                  <span>Workflows {run.summary?.workflows_created ?? 0}</span>
                  <span>Listings {run.summary?.listings_created ?? 0}</span>
                </div>
              </button>
            ))}
            {!runs.length && <div className="text-sm text-muted">No founder runs yet.</div>}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="app-surface">
            <CardHeader>
              <CardTitle className="heading-serif">Weekly Trend Lines</CardTitle>
              <CardDescription>Trajectory across the last runs.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-border/60 bg-surface-2/60 p-4">
                <p className="text-xs text-muted">Agents Created</p>
                <p className="text-2xl font-semibold">{runDetail?.summary?.agents_created ?? 0}</p>
                <TrendSparkline values={trendSeries.agents} />
              </div>
              <div className="rounded-lg border border-border/60 bg-surface-2/60 p-4">
                <p className="text-xs text-muted">Workflows Created</p>
                <p className="text-2xl font-semibold">{runDetail?.summary?.workflows_created ?? 0}</p>
                <TrendSparkline values={trendSeries.workflows} />
              </div>
              <div className="rounded-lg border border-border/60 bg-surface-2/60 p-4">
                <p className="text-xs text-muted">Listings Published</p>
                <p className="text-2xl font-semibold">{runDetail?.summary?.listings_created ?? 0}</p>
                <TrendSparkline values={trendSeries.listings} />
              </div>
            </CardContent>
          </Card>

          <Card className="app-surface">
            <CardHeader>
              <CardTitle className="heading-serif">Run Details</CardTitle>
              <CardDescription>Automation ideas, assets, and market signals.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted">
              {runDetail ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>Status</span>
                    <Badge variant="outline">{runDetail.status}</Badge>
                  </div>
                  {runDetail.error && (
                    <div className="rounded-md border border-red-500/40 bg-red-500/10 p-3 text-red-200">
                      {runDetail.error}
                    </div>
                  )}
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted">Ideas</p>
                      <p className="text-lg font-semibold text-white">
                        {runDetail.automation_ideas?.length ?? 0}
                      </p>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted">Templates</p>
                      <p className="text-lg font-semibold text-white">
                        {(runDetail.templates_published?.agents?.length ?? 0) +
                          (runDetail.templates_published?.workflows?.length ?? 0) +
                          (runDetail.templates_published?.tools?.length ?? 0)}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted">Automation Ideas</p>
                    <ul className="mt-2 space-y-2">
                      {(runDetail.automation_ideas || []).slice(0, 5).map((idea: any) => (
                        <li key={idea.id} className="rounded-md border border-border/60 bg-surface-2/60 p-3">
                          <p className="text-sm font-semibold text-white">{idea.title}</p>
                          <p className="text-xs text-muted">{idea.description}</p>
                        </li>
                      ))}
                      {!runDetail.automation_ideas?.length && (
                        <li className="text-xs text-muted">No automation ideas captured.</li>
                      )}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-muted">Trend Snapshot</p>
                    <div className="mt-2 grid gap-3 md:grid-cols-3">
                      <div className="rounded-md border border-border/60 bg-surface-2/60 p-3">
                        <p className="text-xs text-muted">Top Agents</p>
                        <p className="text-lg font-semibold text-white">
                          {runDetail.trend_snapshot?.top_agents?.length ?? 0}
                        </p>
                      </div>
                      <div className="rounded-md border border-border/60 bg-surface-2/60 p-3">
                        <p className="text-xs text-muted">Top Workflows</p>
                        <p className="text-lg font-semibold text-white">
                          {runDetail.trend_snapshot?.top_workflows?.length ?? 0}
                        </p>
                      </div>
                      <div className="rounded-md border border-border/60 bg-surface-2/60 p-3">
                        <p className="text-xs text-muted">Top Plugins</p>
                        <p className="text-lg font-semibold text-white">
                          {runDetail.trend_snapshot?.top_plugins?.length ?? 0}
                        </p>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted">Select a run to view details.</div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
