"use client";

import { useQuery } from "@tanstack/react-query";
import { billingApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export default function BillingPage() {
  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: billingApi.subscription,
  });
  const { data: usage } = useQuery({ queryKey: ["usage"], queryFn: billingApi.usage });

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Subscription</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted">Plan</p>
              <p className="text-2xl font-semibold">{subscription?.tier || "pro"}</p>
            </div>
            <Badge variant="accent">{subscription?.status || "active"}</Badge>
          </div>
          <div>
            <p className="text-sm text-muted">Monthly Usage</p>
            <Progress value={usage?.usage_percent || 64} />
          </div>
        </CardContent>
      </Card>
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Usage Snapshot</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted">
          <p>Agent Executions: {usage?.agent_runs || 120}</p>
          <p>Workflow Runs: {usage?.workflow_runs || 32}</p>
          <p>Swarm Runs: {usage?.swarm_runs || 8}</p>
          <p>Compute Time: {usage?.compute_hours || 12} hrs</p>
        </CardContent>
      </Card>
    </div>
  );
}
