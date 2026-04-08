"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { innovationApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";

export default function InnovationLabPage() {
  const { data: opportunities = [] } = useQuery({
    queryKey: ["innovation"],
    queryFn: innovationApi.list,
  });
  const [simulation, setSimulation] = useState({ name: "Growth Experiment", hypothesis: "" });

  const simulateMutation = useMutation({
    mutationFn: () =>
      innovationApi.simulate({
        name: simulation.name,
        hypothesis: simulation.hypothesis,
      }),
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[1.3fr_1fr]">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Innovation Opportunities</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted">
          {opportunities.length === 0 && (
            <p>Generate opportunities by running simulations and growth experiments.</p>
          )}
          {opportunities.map((opportunity: any) => (
            <div key={opportunity.id} className="rounded-lg border border-border/60 bg-surface-2/60 p-4">
              <p className="font-semibold">{opportunity.title || "Opportunity"}</p>
              <p className="text-xs text-muted">{opportunity.description}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Run Simulation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            value={simulation.name}
            onChange={(e) => setSimulation((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="Simulation name"
          />
          <Textarea
            value={simulation.hypothesis}
            onChange={(e) => setSimulation((prev) => ({ ...prev, hypothesis: e.target.value }))}
            placeholder="Hypothesis and experiment plan"
          />
          <Button className="w-full" onClick={() => simulateMutation.mutate()}>
            Run Simulation
          </Button>
          {simulateMutation.data && (
            <p className="text-sm text-muted">Simulation queued. Monitor results in dashboards.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
