"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { publicApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type PublicAgent = {
  slug: string;
  name: string;
  description: string;
  short_tagline?: string;
  category?: string;
  cost?: number;
  creator?: string;
  example_execution?: {
    input?: any;
    output?: any;
  };
};

export default function PublicAgentPage({ params }: { params: { slug: string } }) {
  const [agent, setAgent] = useState<PublicAgent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [installing, setInstalling] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    publicApi
      .systemAgent(params.slug)
      .then((data) => {
        if (active) setAgent(data);
      })
      .catch((err) => {
        if (active) setError(err.message || "Failed to load agent.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [params.slug]);

  const handleInstall = async () => {
    setInstalling(true);
    setMessage(null);
    try {
      await publicApi.installSystemAgent(params.slug);
      setMessage("Installed to your workspace.");
    } catch (err: any) {
      setMessage(err.message || "Install failed. Please log in.");
    } finally {
      setInstalling(false);
    }
  };

  const handleShare = async () => {
    const link = `${window.location.origin}/agents/${params.slug}`;
    try {
      await navigator.clipboard.writeText(link);
      setShareStatus("Link copied.");
    } catch {
      setShareStatus(link);
    }
  };

  if (loading) return <div className="p-8">Loading agent page...</div>;
  if (error) return <div className="p-8 text-red-400">{error}</div>;
  if (!agent) return <div className="p-8">Agent not found.</div>;
  const formatValue = (value: any) => {
    if (value === undefined || value === null) return "Example coming soon.";
    return typeof value === "string" ? value : JSON.stringify(value, null, 2);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-8">
      <Link href="/" className="text-sm text-muted hover:text-white">
        &larr; Back to Flowora
      </Link>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif text-3xl">{agent.name}</CardTitle>
          <p className="text-muted">{agent.short_tagline || agent.description}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted">{agent.description}</p>
          <div className="flex flex-wrap gap-3 text-xs text-muted">
            <span>Category: {agent.category || "General"}</span>
            <span>Creator: {agent.creator || "system"}</span>
            <span>Credits: {agent.cost ?? 1}</span>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleInstall} disabled={installing}>
              {installing ? "Installing..." : "Install Agent"}
            </Button>
            <Button variant="outline" onClick={handleShare}>
              Share
            </Button>
          </div>
          {message && <p className="text-sm text-muted">{message}</p>}
          {shareStatus && <p className="text-xs text-muted">{shareStatus}</p>}
        </CardContent>
      </Card>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Example Execution</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <p className="text-muted">Input</p>
            <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-2/60 p-3">
              {formatValue(agent.example_execution?.input)}
            </pre>
          </div>
          <div>
            <p className="text-muted">Output</p>
            <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-2/60 p-3">
              {formatValue(agent.example_execution?.output)}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
