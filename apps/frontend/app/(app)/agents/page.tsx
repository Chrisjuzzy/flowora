"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { agentsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import FloworaLoader from "@/components/FloworaLoader";
import { Bot, PlayCircle } from "lucide-react";

type AgentForm = {
  name: string;
  description: string;
  system_prompt: string;
  tools: string;
  memory: string;
  model: string;
  temperature: number;
};

const initialForm: AgentForm = {
  name: "",
  description: "",
  system_prompt: "You are a helpful AI agent.",
  tools: "web_search, http_request",
  memory: "vector",
  model: "gpt-4o-mini",
  temperature: 0.4,
};

export default function AgentsBuilderPage() {
  const { data: agents = [], refetch, isLoading, isError, error } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });
  const [form, setForm] = useState<AgentForm>(initialForm);
  const [runInput, setRunInput] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  const selectedAgent = useMemo(
    () => agents.find((agent: any) => agent.id === selectedAgentId),
    [agents, selectedAgentId]
  );

  const createMutation = useMutation({
    mutationFn: agentsApi.create,
    onSuccess: () => {
      refetch();
      setForm(initialForm);
      setMessage("Agent saved.");
    },
  });

  const runMutation = useMutation({
    mutationFn: () => agentsApi.run(selectedAgentId || 0, runInput),
    onSuccess: () => setMessage("Agent executed."),
  });

  const handleShare = async (runId: number) => {
    const link = `${window.location.origin}/share/${runId}`;
    try {
      await navigator.clipboard.writeText(link);
      setShareStatus("Share link copied.");
    } catch {
      setShareStatus(link);
    }
  };

  const handleChange = (field: keyof AgentForm, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    const payload = {
      name: form.name,
      description: form.description,
      config: {
        system_prompt: form.system_prompt,
        tools: form.tools.split(",").map((tool) => tool.trim()),
        memory: form.memory,
      },
      ai_provider: "openai",
      model_name: form.model,
      temperature: form.temperature,
    };
    createMutation.mutate(payload);
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
      <FloworaLoader show={runMutation.isPending} />
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Flowora Agent Studio</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {message && <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm">{message}</div>}
          {isLoading && <div className="text-sm text-muted">Loading agents...</div>}
          {isError && <div className="text-sm text-red-400">{(error as Error)?.message}</div>}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label>Agent Name</Label>
              <Input value={form.name} onChange={(e) => handleChange("name", e.target.value)} />
            </div>
            <div>
              <Label>Description</Label>
              <Input value={form.description} onChange={(e) => handleChange("description", e.target.value)} />
            </div>
          </div>

          <Tabs defaultValue="prompt">
            <TabsList>
              <TabsTrigger value="prompt">Prompt</TabsTrigger>
              <TabsTrigger value="tools">Tools</TabsTrigger>
              <TabsTrigger value="memory">Memory</TabsTrigger>
              <TabsTrigger value="execution">Execution</TabsTrigger>
            </TabsList>
            <TabsContent value="prompt">
              <Label>System Prompt</Label>
              <Textarea
                value={form.system_prompt}
                onChange={(e) => handleChange("system_prompt", e.target.value)}
              />
            </TabsContent>
            <TabsContent value="tools">
              <Label>Tools (comma separated)</Label>
              <Input value={form.tools} onChange={(e) => handleChange("tools", e.target.value)} />
              <div className="mt-3 flex items-center gap-3 text-sm text-muted">
                <Switch defaultChecked />
                Enable tool calling and API connectors
              </div>
            </TabsContent>
            <TabsContent value="memory">
              <Label>Memory Strategy</Label>
              <Select value={form.memory} onChange={(e) => handleChange("memory", e.target.value)}>
                <option value="vector">Vector Memory (semantic)</option>
                <option value="short-term">Short-term Context</option>
                <option value="hybrid">Hybrid Memory</option>
              </Select>
              <div className="mt-3 text-sm text-muted">
                Configure long-term memory retention and retrieval weights.
              </div>
            </TabsContent>
            <TabsContent value="execution">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label>Reasoning Model</Label>
                  <Select value={form.model} onChange={(e) => handleChange("model", e.target.value)}>
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="local-llm">Local LLM</option>
                  </Select>
                </div>
                <div>
                  <Label>Temperature</Label>
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={form.temperature}
                    onChange={(e) => handleChange("temperature", Number(e.target.value))}
                  />
                </div>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={createMutation.isPending}>
              Save Agent
            </Button>
            <Button variant="outline">Test Configuration</Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Run Agent</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select
              value={selectedAgentId?.toString() || ""}
              onChange={(e) => setSelectedAgentId(Number(e.target.value))}
            >
              <option value="">Select an agent</option>
              {agents.map((agent: any) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </Select>
            <Textarea
              placeholder="Provide input or task for the agent."
              value={runInput}
              onChange={(e) => setRunInput(e.target.value)}
            />
            <Button
              className="w-full"
              onClick={() => runMutation.mutate()}
              disabled={!selectedAgentId}
            >
              <PlayCircle size={16} /> Run Agent
            </Button>
            {runMutation.data && (
              <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm">
                <p className="text-muted">Result</p>
                <p className="mt-2">{runMutation.data.result || "Execution complete."}</p>
                {runMutation.data.agent_run_id && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => handleShare(runMutation.data.agent_run_id)}
                  >
                    Share result
                  </Button>
                )}
                {shareStatus && <p className="mt-2 text-xs text-muted">{shareStatus}</p>}
              </div>
            )}
            {runMutation.isError && (
              <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm text-red-400">
                {(runMutation.error as Error)?.message || "Run failed."}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Your Agents</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!isLoading && agents.length === 0 && (
              <div className="rounded-lg border border-dashed border-border/60 bg-surface-2/40 p-4 text-sm text-muted">
                No agents yet. Create your first Flowora agent.
              </div>
            )}
            {agents.map((agent: any) => (
              <div key={agent.id} className="flex items-center justify-between rounded-lg border border-border/60 bg-surface-2/60 p-3">
                <div>
                  <p className="font-semibold">{agent.name}</p>
                  <p className="text-xs text-muted">{agent.description}</p>
                </div>
                <Badge>{agent.is_published ? "Published" : "Draft"}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
