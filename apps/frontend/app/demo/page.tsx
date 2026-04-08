"use client";

import { useEffect, useMemo, useState } from "react";
import { publicApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import FloworaLoader from "@/components/FloworaLoader";

const demoTemplates = [
  {
    name: "Startup Idea Generator",
    input: "Give me three AI startup ideas for retail.",
  },
  {
    name: "Marketing Copy Agent",
    input: "Write a product tagline for a smart water bottle.",
  },
  {
    name: "Blog Writer",
    input: "Outline a blog post about AI in healthcare.",
  },
];

export default function DemoPage() {
  const envAgentId = Number(process.env.NEXT_PUBLIC_DEMO_AGENT_ID || 0);
  const [agentId, setAgentId] = useState<number | null>(envAgentId || null);
  const [selectedTemplate, setSelectedTemplate] = useState(demoTemplates[0]);
  const [inputValue, setInputValue] = useState(demoTemplates[0].input);
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [demoReady, setDemoReady] = useState(false);

  const templates = useMemo(() => demoTemplates, []);

  useEffect(() => {
    if (envAgentId) {
      setDemoReady(true);
      return;
    }
    publicApi
      .demoAgent()
      .then((data) => {
        if (data?.id) {
          setAgentId(Number(data.id));
        }
      })
      .catch((err: any) => {
        setError(err?.message || "Demo agent not available.");
      })
      .finally(() => {
        setDemoReady(true);
      });
  }, [envAgentId]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setOutput(null);
    try {
      if (!agentId) {
        setOutput(
          "Demo agent is not available yet. Please try again or ask an admin to seed the demo agent."
        );
        return;
      }
      const result = await publicApi.runAgent(agentId, inputValue);
      const display = typeof result?.result === "string" ? result.result : JSON.stringify(result?.result, null, 2);
      setOutput(display || "Execution completed.");
    } catch (err: any) {
      setError(err.message || "Demo run failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-6 py-12">
      <FloworaLoader show={running} />

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif text-3xl">Interactive Demo</CardTitle>
          <p className="text-muted">
            Test a public Flowora agent instantly. Choose a template and run it.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {templates.map((template) => (
              <button
                key={template.name}
                onClick={() => {
                  setSelectedTemplate(template);
                  setInputValue(template.input);
                }}
                className={`rounded-full border px-3 py-1 text-xs ${
                  selectedTemplate.name === template.name
                    ? "border-accent text-white"
                    : "border-border text-muted"
                }`}
              >
                {template.name}
              </button>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-[200px_1fr]">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted">Agent ID</p>
              <Input
                type="number"
                value={agentId ?? ""}
                onChange={(e) => setAgentId(Number(e.target.value))}
                placeholder="Public Agent ID"
              />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-muted">Input</p>
              <Input value={inputValue} onChange={(e) => setInputValue(e.target.value)} />
            </div>
          </div>

          <Button onClick={handleRun} disabled={running || !demoReady}>
            Run Agent
          </Button>
          {error && <p className="text-sm text-red-400">{error}</p>}
        </CardContent>
      </Card>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Live Output</CardTitle>
        </CardHeader>
        <CardContent>
          {output ? (
            <pre className="whitespace-pre-wrap rounded-lg bg-surface-2/60 p-4 text-sm">{output}</pre>
          ) : (
            <div className="rounded-lg border border-dashed border-border/60 bg-surface-2/40 p-6 text-sm text-muted">
              Run the demo to see output here.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
