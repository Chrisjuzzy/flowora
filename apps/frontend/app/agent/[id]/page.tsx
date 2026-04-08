"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function PublicAgentPage() {
  const params = useParams();
  const agentId = params?.id as string;
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!agentId) return;
    fetch(`${API_URL}/agents/public/${agentId}`)
      .then((res) => res.json())
      .then((data) => setAgent(data))
      .catch(() => setAgent(null))
      .finally(() => setLoading(false));
  }, [agentId]);

  const install = async () => {
    setStatus(null);
    try {
      await api.post(`/marketplace/${agentId}/install`);
      setStatus("Installed successfully.");
    } catch (err: any) {
      setStatus(err?.message || "Install failed.");
    }
  };

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const shareLink = typeof window !== "undefined" ? window.location.href : "";
  const embedCode = `<script src="${origin}/platform-agent.js" data-agent-id="${agentId}" data-base-url="${origin}" data-height="600"></script>`;

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      setCopied("Copy failed");
    }
  };

  if (loading) {
    return <div className="p-10">Loading...</div>;
  }

  if (!agent) {
    return <div className="p-10">Agent not found.</div>;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-10">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold">{agent.name}</h1>
        <p className="text-slate-300 mt-2">{agent.description}</p>
        <div className="mt-4 text-sm text-slate-400">
          Rating: {agent.rating?.toFixed?.(2) || agent.rating || "N/A"}
        </div>
        <div className="mt-6 flex gap-3">
          <button
            onClick={install}
            className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-md text-sm font-semibold"
          >
            Install Agent
          </button>
          <button
            onClick={() => copyToClipboard(shareLink, "Link copied")}
            className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-md text-sm font-semibold"
          >
            Share
          </button>
        </div>
        {status && <div className="mt-4 text-sm text-slate-300">{status}</div>}

        <div className="mt-8 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Embed This Agent</h2>
            <button
              onClick={() => copyToClipboard(embedCode, "Embed code copied")}
              className="text-xs text-indigo-300 hover:text-indigo-200"
            >
              Copy Embed Code
            </button>
          </div>
          <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-300 bg-black/50 rounded p-3">
            {embedCode}
          </pre>
          {copied && <div className="mt-2 text-xs text-emerald-300">{copied}</div>}
        </div>
      </div>
    </div>
  );
}
