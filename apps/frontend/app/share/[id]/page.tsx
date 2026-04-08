"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { shareApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type SharedRun = {
  id: number;
  agent_id: number;
  agent_name: string;
  agent_description?: string;
  input_prompt?: string;
  output_response: string;
  created_at: string;
};

export default function SharePage({ params }: { params: { id: string } }) {
  const [run, setRun] = useState<SharedRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    shareApi
      .get(Number(params.id))
      .then(setRun)
      .catch((err) => setError(err.message || "Share not found."));
  }, [params.id]);

  if (error) return <div className="p-8 text-red-400">{error}</div>;
  if (!run) return <div className="p-8">Loading share...</div>;

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-6 py-12">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">{run.agent_name}</CardTitle>
          <p className="text-muted">{run.agent_description}</p>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <p className="text-muted">User Input</p>
            <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-2/60 p-3">
              {run.input_prompt || "No input provided."}
            </pre>
          </div>
          <div>
            <p className="text-muted">AI Result</p>
            <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-2/60 p-3">
              {run.output_response}
            </pre>
          </div>
          <div className="flex gap-3">
            <Link href={`/a/${run.agent_id}`}>
              <Button>Try this agent</Button>
            </Link>
            <Link href="/demo">
              <Button variant="outline">Run demo</Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
