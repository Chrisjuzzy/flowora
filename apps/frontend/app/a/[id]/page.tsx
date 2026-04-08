"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { agentsApi, marketplaceApi, publicApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type PublicAgent = {
  id: number;
  name: string;
  description?: string;
  category?: string;
  tags?: string;
  rating?: number;
  is_published?: boolean;
};

export default function ShareAgentPage({ params }: { params: { id: string } }) {
  const agentId = Number(params.id);
  const router = useRouter();
  const [agent, setAgent] = useState<PublicAgent | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    publicApi
      .agent(agentId)
      .then((data) => {
        if (active) setAgent(data);
      })
      .catch((err) => {
        if (active) setMessage(err.message || "Unable to load agent.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [agentId]);

  const handleInstall = async () => {
    setMessage(null);
    try {
      await marketplaceApi.install(agentId);
      setMessage("Installed to your workspace.");
      router.push("/dashboard");
    } catch (err: any) {
      setMessage(err.message || "Install failed. Please log in.");
    }
  };

  const handleClone = async () => {
    setMessage(null);
    try {
      await agentsApi.clone(agentId);
      setMessage("Cloned to your workspace.");
      router.push("/agents");
    } catch (err: any) {
      setMessage(err.message || "Clone failed. Please log in.");
    }
  };

  const handleShare = async () => {
    const link = `${window.location.origin}/a/${agentId}`;
    try {
      await navigator.clipboard.writeText(link);
      setShareStatus("Link copied.");
    } catch {
      setShareStatus(link);
    }
  };

  if (loading) return <div className="p-8">Loading agent preview...</div>;
  if (!agent) return <div className="p-8">{message || "Agent not found."}</div>;

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-8">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif text-3xl">{agent.name}</CardTitle>
          <p className="text-muted">{agent.description}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-3 text-xs text-muted">
            <span>Category: {agent.category || "General"}</span>
            <span>Rating: {agent.rating?.toFixed(1) || "4.8"}</span>
            <span>{agent.is_published ? "Public" : "Private"}</span>
          </div>
          <div className="flex gap-3">
            <Button onClick={handleInstall}>Install to Workspace</Button>
            <Button variant="outline" onClick={handleClone}>
              Clone Agent
            </Button>
            <Button variant="secondary" onClick={handleShare}>
              Share
            </Button>
          </div>
          {message && <p className="text-sm text-muted">{message}</p>}
          {shareStatus && <p className="text-xs text-muted">{shareStatus}</p>}
          <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-xs text-muted">
            Embed this agent:
            <pre className="mt-2 whitespace-pre-wrap">{`<iframe src="https://flowora.ai/embed/${agentId}"></iframe>`}</pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
