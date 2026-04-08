"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAgent, getExecutions, runAgent, getAgentVersions, createAgentVersion, rollbackAgentVersion, publishAgent, createListing } from '@/lib/api';
import { Agent, Execution, AgentVersion } from '@/types';
import RunAgentModal from '@/components/RunAgentModal';
import ExecutionViewer, { ExecutionResult } from '@/components/ExecutionViewer';

export default function AgentDetails({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [newVersion, setNewVersion] = useState({ version: '', description: '' });
  const [publishData, setPublishData] = useState({ tags: '', category: '', price: 0 });
  const [shareCopied, setShareCopied] = useState<string | null>(null);
  const router = useRouter();
  const id = parseInt(params.id);

  const fetchData = async () => {
    try {
      const [agentData, executionsData] = await Promise.all([
        getAgent(id),
        getExecutions(id)
      ]);
      setAgent(agentData);
      setExecutions(executionsData);
      
      // Fetch versions if user owns the agent
      if (agentData.owner_id) {
        try {
            const versionsData = await getAgentVersions(id);
            setVersions(versionsData);
        } catch (e) {
            console.log("Could not fetch versions (might not be owner)");
        }
      }
    } catch (error) {
      console.error('Failed to fetch data', error);
      // router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleCreateVersion = async () => {
    if (!newVersion.version) return alert("Version string required");
    try {
        await createAgentVersion(id, newVersion.version, newVersion.description);
        setNewVersion({ version: '', description: '' });
        fetchData(); // Refresh
        alert("Version snapshot created!");
    } catch (e: any) {
        alert("Failed to create version: " + e.message);
    }
  };

  const handleRollback = async (versionId: number) => {
    if (!confirm("Are you sure? This will overwrite current configuration.")) return;
    try {
        await rollbackAgentVersion(id, versionId);
        fetchData();
        alert("Rolled back successfully!");
    } catch (e: any) {
        alert("Rollback failed: " + e.message);
    }
  };

  const handlePublish = async () => {
    try {
        await publishAgent(id, { 
            tags: publishData.tags, 
            category: publishData.category,
            version: agent?.version 
        });
        
        if (publishData.price >= 0) {
            await createListing({
              agent_id: id,
              price: publishData.price,
              category: publishData.category,
              is_active: true,
              listing_type: "agent",
            });
        }
        
        alert("Agent published to marketplace!");
    } catch (e: any) {
        alert("Publish failed: " + e.message);
    }
  };


  const handleRunSuccess = (result: ExecutionResult) => {
    setExecutionResult(result);
    fetchData(); // Refresh history
  };

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const shareLink = origin ? `${origin}/agent/${id}` : "";
  const embedCode = origin
    ? `<script src="${origin}/platform-agent.js" data-agent-id="${id}" data-base-url="${origin}" data-height="600"></script>`
    : "";

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setShareCopied(label);
      setTimeout(() => setShareCopied(null), 1500);
    } catch {
      setShareCopied("Copy failed");
    }
  };

  if (loading) {
    return (
        <div className="flex justify-center items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-accent"></div>
        </div>
    );
  }

  if (!agent) {
    return <div className="text-center text-muted">Agent not found</div>;
  }

  return (
      <div className="space-y-6">
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{agent.name}</h1>
              {!agent.owner_id && (
                <span className="bg-surface-2/60 text-white text-xs px-2 py-1 rounded-full">
                  System Template
                </span>
              )}
            </div>
            <p className="text-muted max-w-2xl">{agent.description}</p>
          </div>
          <button
            onClick={() => setIsRunModalOpen(true)}
            className="px-6 py-2 bg-accent text-black rounded-lg hover:bg-amber-300 font-medium transition-colors"
          >
            Run Agent
          </button>
        </div>

        {/* Configuration Section (if user owns it or system) */}
        <div className="app-surface p-6 rounded-lg mb-8">
          <h2 className="text-lg font-bold mb-4">Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-muted mb-1">System Prompt</label>
              <div className="bg-surface-2/60 p-4 rounded-md text-sm font-mono text-white whitespace-pre-wrap max-h-48 overflow-y-auto border border-border">
                {agent.config?.system_prompt || 'No system prompt configured.'}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-muted mb-1">User Prompt Template</label>
              <div className="bg-surface-2/60 p-4 rounded-md text-sm font-mono text-white whitespace-pre-wrap max-h-48 overflow-y-auto border border-border">
                {agent.config?.prompt || '{input}'}
              </div>
            </div>
          </div>
        </div>

        {/* Version Control */}
        {agent.owner_id && (
          <div className="app-surface p-6 rounded-lg mb-8">
            <h2 className="text-lg font-bold mb-4 flex justify-between">
              <span>Version History</span>
              <span className="text-sm font-normal text-muted">Current: v{agent.version || '1.0.0'}</span>
            </h2>
            
            <div className="mb-6 bg-surface-2/60 p-4 rounded-lg">
              <h3 className="text-sm font-bold mb-2">Create New Version</h3>
              <div className="flex gap-4">
                <input 
                  type="text" 
                  placeholder="Version (e.g. 1.0.1)" 
                  className="border border-border rounded px-3 py-2 text-sm w-32 bg-surface-2/60 text-white"
                  value={newVersion.version}
                  onChange={e => setNewVersion({...newVersion, version: e.target.value})}
                />
                <input 
                  type="text" 
                  placeholder="Changelog description" 
                  className="border border-border rounded px-3 py-2 text-sm flex-1 bg-surface-2/60 text-white"
                  value={newVersion.description}
                  onChange={e => setNewVersion({...newVersion, description: e.target.value})}
                />
                <button 
                  onClick={handleCreateVersion}
                  className="bg-accent text-black px-4 py-2 rounded text-sm hover:bg-amber-300"
                >
                  Snapshot
                </button>
              </div>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {versions.length === 0 ? <p className="text-sm text-muted">No version history.</p> : versions.map(v => (
                <div key={v.id} className="flex justify-between items-center p-3 border border-border rounded hover:bg-surface-2/40">
                  <div>
                    <span className="font-bold">v{v.version}</span>
                    <span className="text-muted text-xs ml-2">{new Date(v.created_at).toLocaleString()}</span>
                    <p className="text-xs text-muted">{v.description || 'No description'}</p>
                  </div>
                  {v.version !== agent.version && (
                    <button 
                      onClick={() => handleRollback(v.id)}
                      className="text-accent text-xs border border-border px-2 py-1 rounded hover:bg-surface-2/60"
                    >
                      Rollback
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Publishing */}
        {agent.owner_id && (
            <div className="app-surface p-6 rounded-lg mb-8">
                <h2 className="text-lg font-bold mb-4">Publish to Marketplace</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm text-muted mb-1">Tags (comma separated)</label>
                        <input 
                            type="text" 
                            className="w-full border border-border rounded px-3 py-2 text-sm bg-surface-2/60 text-white" 
                            placeholder="e.g. finance, analysis"
                            value={publishData.tags}
                            onChange={e => setPublishData({...publishData, tags: e.target.value})}
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-muted mb-1">Category</label>
                        <select 
                            className="w-full border border-border rounded px-3 py-2 text-sm bg-surface-2/60 text-white"
                            value={publishData.category}
                            onChange={e => setPublishData({...publishData, category: e.target.value})}
                        >
                            <option value="">Select Category</option>
                            <option value="business">Business</option>
                            <option value="coding">Coding</option>
                            <option value="writing">Writing</option>
                            <option value="data">Data Analysis</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm text-muted mb-1">Price ($)</label>
                        <input 
                            type="number" 
                            className="w-full border border-border rounded px-3 py-2 text-sm bg-surface-2/60 text-white" 
                            min="0"
                            value={publishData.price}
                            onChange={e => setPublishData({...publishData, price: parseFloat(e.target.value)})}
                        />
                    </div>
                </div>
                <div className="mt-4">
                    <button 
                        onClick={handlePublish}
                        className="bg-accent text-black px-6 py-2 rounded-lg font-medium hover:bg-amber-300 transition"
                    >
                        Publish Agent
                    </button>
                </div>
            </div>
        )}

        {/* Public Share */}
        <div className="app-surface p-6 rounded-lg mb-8">
          <h2 className="text-lg font-bold mb-2">Share Publicly</h2>
          <p className="text-sm text-muted">
            Share link and embed code for this agent. Public link requires publishing.
          </p>
          {!agent.is_published && (
            <p className="text-xs text-amber-300 mt-2">
              This agent is not published yet. Publish to enable public access.
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={() => copyToClipboard(shareLink, "Link copied")}
              className="bg-surface-2/60 text-white px-4 py-2 rounded text-sm hover:bg-surface-2/90"
              disabled={!shareLink}
            >
              Copy Public Link
            </button>
            <button
              onClick={() => copyToClipboard(embedCode, "Embed copied")}
              className="bg-surface-2/60 text-white px-4 py-2 rounded text-sm hover:bg-surface-2/90"
              disabled={!embedCode}
            >
              Copy Embed Code
            </button>
          </div>
          {embedCode && (
            <pre className="mt-3 whitespace-pre-wrap text-xs text-muted bg-surface-2/40 rounded p-3">
              {embedCode}
            </pre>
          )}
          {shareCopied && <div className="mt-2 text-xs text-emerald-300">{shareCopied}</div>}
        </div>

        {/* Execution History */}
        <div className="app-surface rounded-lg">
          <div className="px-6 py-4 border-b border-border">
            <h2 className="text-lg font-bold">Execution History</h2>
          </div>
          {executions.length === 0 ? (
            <div className="p-8 text-center text-muted">
              No executions yet. Run the agent to see results here.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-muted">
                <thead className="bg-surface-2/60 text-muted uppercase font-semibold">
                  <tr>
                    <th className="px-6 py-3">ID</th>
                    <th className="px-6 py-3">Prompt</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Result Preview</th>
                    <th className="px-6 py-3">Date</th>
                    <th className="px-6 py-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {executions.map((exec) => (
                    <tr key={exec.id} className="hover:bg-surface-2/40 transition-colors">
                      <td className="px-6 py-4 font-mono">#{exec.id}</td>
                      <td className="px-6 py-4 text-xs text-muted">
                        {exec.prompt_version_id ? `v${exec.prompt_version_id}` : "-"}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          exec.status === 'completed' ? 'bg-green-500/20 text-green-300' : 
                          exec.status === 'failed' ? 'bg-red-500/20 text-red-300' : 'bg-surface-2/60 text-white'
                        }`}>
                          {exec.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 max-w-xs truncate" title={exec.result}>
                        {exec.result}
                      </td>
                      <td className="px-6 py-4">
                        {new Date(exec.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4">
                        <button 
                          onClick={() => setExecutionResult({
                            status: exec.status,
                            result: exec.result,
                            execution_id: exec.id,
                            prompt_version_id: exec.prompt_version_id
                          })}
                          className="text-accent hover:text-amber-300 font-medium"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <RunAgentModal
          isOpen={isRunModalOpen}
          onClose={() => setIsRunModalOpen(false)}
          agent={agent}
          onSuccess={handleRunSuccess}
        />
        
        <ExecutionViewer 
            result={executionResult} 
            onClose={() => setExecutionResult(null)} 
        />
      </div>
  );
}
