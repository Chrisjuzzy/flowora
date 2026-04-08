"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { agentsApi, templatesApi } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

interface TemplateItem {
  id: number;
  name: string;
  description?: string;
  category?: string;
  tags?: string;
  base_config?: Record<string, any>;
  tools?: string[];
  slug: string;
  share_url?: string;
  install_count?: number;
  share_count?: number;
  created_at?: string;
  creator?: { id: number; email: string } | null;
}

interface AgentItem {
  id: number;
  name: string;
}

export default function TemplatesClient() {
  const searchParams = useSearchParams();
  const welcome = searchParams.get("welcome") === "1";
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [installingId, setInstallingId] = useState<number | null>(null);
  const [sharingId, setSharingId] = useState<number | null>(null);
  const [showSubmit, setShowSubmit] = useState(false);
  const [submitState, setSubmitState] = useState({
    agentId: "",
    name: "",
    description: "",
    category: "",
    tags: "",
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [templatesData, agentsData] = await Promise.all([templatesApi.list(), agentsApi.list()]);
      setTemplates(templatesData || []);
      setAgents(agentsData || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load templates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const trending = useMemo(() => {
    return [...templates]
      .sort((a, b) => (b.install_count || 0) - (a.install_count || 0))
      .slice(0, 6);
  }, [templates]);

  const newest = useMemo(() => {
    return [...templates]
      .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())
      .slice(0, 6);
  }, [templates]);

  const topInstalled = useMemo(() => {
    return [...templates]
      .sort((a, b) => (b.install_count || 0) - (a.install_count || 0))
      .slice(0, 12);
  }, [templates]);

  const handleInstall = async (template: TemplateItem) => {
    setInstallingId(template.id);
    setMessage(null);
    try {
      const response = await templatesApi.install(template.id);
      setMessage(`${template.name} installed to your workspace.`);
      setTemplates((prev) =>
        prev.map((item) =>
          item.id === template.id ? { ...item, install_count: response.install_count } : item
        )
      );
    } catch (err: any) {
      setMessage(err?.message || "Install failed.");
    } finally {
      setInstallingId(null);
    }
  };

  const handleShare = async (template: TemplateItem) => {
    setSharingId(template.id);
    setMessage(null);
    try {
      const url = `${window.location.origin}/templates/${template.slug}`;
      if (navigator.share) {
        await navigator.share({ title: template.name, text: template.description || "", url });
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
      }
      await templatesApi.share(template.id);
      setMessage("Share link ready. Paste it anywhere to spread Flowora.");
    } catch (err: any) {
      setMessage(err?.message || "Share failed.");
    } finally {
      setSharingId(null);
    }
  };

  const handleSubmitTemplate = async () => {
    setMessage(null);
    try {
      await templatesApi.submit({
        agent_id: Number(submitState.agentId),
        name: submitState.name || undefined,
        description: submitState.description || undefined,
        category: submitState.category || undefined,
        tags: submitState.tags || undefined,
      });
      setMessage("Template submitted to the library.");
      setShowSubmit(false);
      setSubmitState({ agentId: "", name: "", description: "", category: "", tags: "" });
      await loadData();
    } catch (err: any) {
      setMessage(err?.message || "Submit failed.");
    }
  };

  const renderTags = (tags?: string) => {
    if (!tags) return null;
    return tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
      .slice(0, 4)
      .map((tag) => (
        <Badge key={tag} className="text-xs">
          {tag}
        </Badge>
      ));
  };

  const renderSection = (title: string, items: TemplateItem[]) => (
    <section className="mt-10">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{title}</h2>
      </div>
      <div className="mt-4 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {items.map((template) => (
          <div key={template.id} className="rounded-2xl border border-border bg-surface-2/60 p-6">
            <div className="flex items-center justify-between">
              <Link href={`/templates/${template.slug}`} className="text-lg font-semibold hover:text-accent">
                {template.name}
              </Link>
              <span className="text-xs text-muted">{template.install_count || 0} installs</span>
            </div>
            <p className="mt-2 text-sm text-muted">{template.description}</p>
            <div className="mt-3 flex flex-wrap gap-2">{renderTags(template.tags)}</div>
            <div className="mt-6 flex flex-col gap-2">
              <Button
                onClick={() => handleInstall(template)}
                disabled={installingId === template.id}
              >
                {installingId === template.id ? "Installing..." : "Install Template"}
              </Button>
              <Button
                variant="outline"
                onClick={() => handleShare(template)}
                disabled={sharingId === template.id}
              >
                {sharingId === template.id ? "Sharing..." : "Share Template"}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold heading-serif">Template Library</h1>
          <p className="text-muted">Discover and install ready-made Flowora agents.</p>
          {welcome && (
            <div className="mt-4 rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm text-muted">
              Welcome aboard! Start by installing one of these starter agents.
            </div>
          )}
          {message && (
            <div className="mt-4 rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm">
              {message}
            </div>
          )}
          {error && (
            <div className="mt-4 rounded-lg border border-border/60 bg-red-500/10 p-3 text-sm text-red-200">
              {error}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-surface-2/40 p-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold">Publish your own agent template</h3>
            <p className="text-sm text-muted">Share your best agents with the Flowora community.</p>
          </div>
          <Button variant="secondary" onClick={() => setShowSubmit((prev) => !prev)}>
            {showSubmit ? "Close" : "Submit Template"}
          </Button>
        </div>

        {showSubmit && (
          <div className="mt-6 rounded-2xl border border-border bg-surface-2/60 p-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Agent</label>
                <select
                  className="mt-2 h-10 w-full rounded-md border border-border bg-surface-2/60 px-3 text-sm"
                  value={submitState.agentId}
                  onChange={(event) => setSubmitState((prev) => ({ ...prev, agentId: event.target.value }))}
                >
                  <option value="">Select an agent</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Template Name</label>
                <Input
                  className="mt-2"
                  placeholder="Optional override"
                  value={submitState.name}
                  onChange={(event) => setSubmitState((prev) => ({ ...prev, name: event.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Category</label>
                <Input
                  className="mt-2"
                  placeholder="marketing, growth, ops"
                  value={submitState.category}
                  onChange={(event) => setSubmitState((prev) => ({ ...prev, category: event.target.value }))}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Description</label>
                <Textarea
                  className="mt-2"
                  placeholder="What does this agent do best?"
                  value={submitState.description}
                  onChange={(event) => setSubmitState((prev) => ({ ...prev, description: event.target.value }))}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs uppercase tracking-[0.2em] text-muted">Tags</label>
                <Input
                  className="mt-2"
                  placeholder="comma-separated tags"
                  value={submitState.tags}
                  onChange={(event) => setSubmitState((prev) => ({ ...prev, tags: event.target.value }))}
                />
              </div>
            </div>
            <div className="mt-6 flex items-center gap-3">
              <Button onClick={handleSubmitTemplate} disabled={!submitState.agentId}>
                Publish Template
              </Button>
              <span className="text-xs text-muted">Your agent will appear in the library once approved.</span>
            </div>
          </div>
        )}

        {loading ? (
          <div className="mt-10 text-sm text-muted">Loading templates...</div>
        ) : (
          <>
            {renderSection("Trending Templates", trending)}
            {renderSection("New Templates", newest)}
            {renderSection("Top Installed Templates", topInstalled)}
          </>
        )}
      </main>
    </div>
  );
}
