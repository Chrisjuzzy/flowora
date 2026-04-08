"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function EmbeddedAgentPage() {
  const params = useParams();
  const search = useSearchParams();
  const agentId = params?.id as string;
  const theme = useMemo(() => search?.get("theme") || "light", [search]);
  const [agent, setAgent] = useState<any>(null);
  const [input, setInput] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!agentId) return;
    fetch(`${API_URL}/agents/public/${agentId}`)
      .then((res) => res.json())
      .then((data) => setAgent(data))
      .catch(() => setAgent(null));
  }, [agentId]);

  const runAgent = async () => {
    if (!input) return;
    setLoading(true);
    setResponse(null);
    try {
      const res = await fetch(`${API_URL}/agents/public/${agentId}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input_data: input }),
      });
      const data = await res.json();
      setResponse(data.result || data.error || "No response");
    } catch (err: any) {
      setResponse(err?.message || "Execution failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`min-h-screen p-4 ${
        theme === "dark" ? "bg-gray-900 text-white" : "bg-white text-gray-900"
      }`}
    >
      <div className="max-w-xl mx-auto border rounded-xl p-4 shadow-sm">
        <h1 className="text-lg font-semibold">{agent?.name || "Agent"}</h1>
        <p className="text-sm opacity-70 mb-4">
          {agent?.description || "Embedded agent"}
        </p>
        <textarea
          className="w-full border rounded-md p-2 text-sm mb-2 text-gray-900"
          rows={4}
          placeholder="Ask the agent something..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          className="w-full bg-indigo-600 text-white rounded-md py-2 text-sm font-semibold disabled:opacity-60"
          onClick={runAgent}
          disabled={loading}
        >
          {loading ? "Running..." : "Run Agent"}
        </button>
        {response && (
          <div className="mt-3 p-3 rounded-md bg-gray-100 text-gray-900 text-sm whitespace-pre-wrap">
            {response}
          </div>
        )}
      </div>
    </div>
  );
}
