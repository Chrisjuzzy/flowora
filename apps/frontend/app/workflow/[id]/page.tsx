"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function PublicWorkflowPage() {
  const params = useParams();
  const workflowId = params?.id as string;
  const [workflow, setWorkflow] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!workflowId) return;
    fetch(`${API_URL}/workflows/public/${workflowId}`)
      .then((res) => res.json())
      .then((data) => setWorkflow(data))
      .catch(() => setWorkflow(null))
      .finally(() => setLoading(false));
  }, [workflowId]);

  const cloneWorkflow = async () => {
    setStatus(null);
    try {
      await api.post(`/workflows/${workflowId}/clone`);
      setStatus("Workflow cloned.");
    } catch (err: any) {
      setStatus(err?.message || "Clone failed.");
    }
  };

  const installWorkflow = async () => {
    setStatus(null);
    try {
      await api.post(`/workflows/${workflowId}/install`);
      setStatus("Workflow installed.");
    } catch (err: any) {
      setStatus(err?.message || "Install failed.");
    }
  };

  const shareLink = typeof window !== "undefined" ? window.location.href : "";

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

  if (!workflow) {
    return <div className="p-10">Workflow not found.</div>;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-10">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold">{workflow.name}</h1>
        <p className="text-slate-300 mt-2">{workflow.description}</p>
        <div className="mt-4 text-sm text-slate-400">
          Clones: {workflow.clone_count || 0} | Installs: {workflow.install_count || 0}
        </div>
        <div className="mt-6 flex gap-3">
          <button
            onClick={cloneWorkflow}
            className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-md text-sm font-semibold"
          >
            Clone Workflow
          </button>
          <button
            onClick={installWorkflow}
            className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-md text-sm font-semibold"
          >
            Install Workflow
          </button>
          <button
            onClick={() => copyToClipboard(shareLink, "Link copied")}
            className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-md text-sm font-semibold"
          >
            Share
          </button>
        </div>
        {status && <div className="mt-4 text-sm text-slate-300">{status}</div>}
        {copied && <div className="mt-2 text-xs text-emerald-300">{copied}</div>}
      </div>
    </div>
  );
}
