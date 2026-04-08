"use client";

import { useQuery } from "@tanstack/react-query";
import { agentsApi, analyticsApi, executionsApi, marketplaceApi, walletApi } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Activity, Bot, CreditCard, Sparkles } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: agentsApi.list });
  const { data: executions = [] } = useQuery({ queryKey: ["executions"], queryFn: executionsApi.list });
  const { data: listings = [] } = useQuery({ queryKey: ["marketplace"], queryFn: marketplaceApi.listings });
  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: walletApi.balance });
  const { data: founderRuns } = useQuery({
    queryKey: ["founder-runs"],
    queryFn: () => analyticsApi.founderRuns(3),
  });

  const latestFounderRun = founderRuns?.runs?.[0];

  const activeAgents = agents.filter((agent: any) => agent.owner_id);
  const systemAgents = agents.filter((agent: any) => !agent.owner_id);

  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-4">
        <Card className="app-surface">
          <CardHeader>
            <CardDescription>Total Agents</CardDescription>
            <CardTitle className="text-3xl">{agents.length}</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between text-muted">
            <span>{activeAgents.length} personal</span>
            <Bot size={18} />
          </CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardDescription>Executions</CardDescription>
            <CardTitle className="text-3xl">{executions.length}</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between text-muted">
            <span>Last 24h</span>
            <Activity size={18} />
          </CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardDescription>Wallet Balance</CardDescription>
            <CardTitle className="text-3xl">${wallet?.balance ?? 0}</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between text-muted">
            <span>Credits available</span>
            <CreditCard size={18} />
          </CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardDescription>Marketplace</CardDescription>
            <CardTitle className="text-3xl">{listings.length}</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between text-muted">
            <span>Live listings</span>
            <Sparkles size={18} />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Execution Pulse</CardTitle>
            <CardDescription>Monitor your agent runtime in real time.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted">Success Rate</p>
                <p className="text-2xl font-semibold">92%</p>
              </div>
              <Badge variant="accent">Stable</Badge>
            </div>
            <Progress value={92} />
            <div className="grid gap-3 md:grid-cols-2">
              {executions.slice(0, 4).map((execution: any) => (
                <div key={execution.id} className="rounded-lg border border-border/60 bg-surface-2/60 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-muted">
                      Agent #{execution.agent_id}
                      {execution.prompt_version_id ? ` - v${execution.prompt_version_id}` : ""}
                    </p>
                    <Badge variant="outline">{execution.status}</Badge>
                  </div>
                  <p className="mt-2 text-sm">{execution.result?.slice(0, 80) || "Execution log"}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="app-surface">
            <CardHeader>
              <CardTitle className="heading-serif">System Templates</CardTitle>
              <CardDescription>Curated agents ready to deploy.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {systemAgents.slice(0, 3).map((agent: any) => (
                <div key={agent.id} className="rounded-lg border border-border/60 bg-surface-2/50 p-4">
                  <p className="font-semibold">{agent.name}</p>
                  <p className="text-xs text-muted">{agent.description}</p>
                  <Button variant="secondary" size="sm" className="mt-3 w-full">
                    Clone to Workspace
                  </Button>
                </div>
              ))}
              <Button variant="outline" className="w-full">
                Browse Marketplace
              </Button>
            </CardContent>
          </Card>

          <Card className="app-surface">
            <CardHeader>
              <CardTitle className="heading-serif">Founder Mode Weekly</CardTitle>
              <CardDescription>Automated launches and growth assets.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted">
              {latestFounderRun ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>Status</span>
                    <Badge variant="outline">{latestFounderRun.status}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Agents Created</span>
                    <span>{latestFounderRun.summary?.agents_created ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Workflows Created</span>
                    <span>{latestFounderRun.summary?.workflows_created ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Listings Published</span>
                    <span>{latestFounderRun.summary?.listings_created ?? 0}</span>
                  </div>
                </>
              ) : (
                <div>No weekly runs yet.</div>
              )}
              <Button variant="outline" size="sm" className="w-full" asChild>
                <Link href="/founder-mode">Open Founder Mode</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
