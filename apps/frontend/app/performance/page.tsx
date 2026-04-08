"use client";
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getDashboardStats, getReflections, getEvolutions, applyEvolution } from '@/lib/api';

interface Stats {
  total_memories: number;
  total_reflections: number;
  avg_confidence: number;
  flagged_executions: number;
  pending_evolutions: number;
}

interface Reflection {
  id: number;
  confidence_score: number;
  critique: string;
  suggestions: string;
  is_flagged: boolean;
  created_at: string;
}

interface Evolution {
  id: number;
  issue_detected: string;
  proposed_prompt: string;
  status: string;
  created_at: string;
}

export default function PerformanceDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [reflections, setReflections] = useState<Reflection[]>([]);
  const [evolutions, setEvolutions] = useState<Evolution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsData, refData, evoData] = await Promise.all([
        getDashboardStats(),
        getReflections(undefined, true), // Get flagged only for main view
        getEvolutions()
      ]);
      setStats(statsData);
      setReflections(refData);
      setEvolutions(evoData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyEvolution = async (id: number) => {
    try {
      await applyEvolution(id);
      alert("Evolution applied successfully! Agent prompt updated.");
      fetchData();
    } catch (e) {
      alert("Failed to apply evolution.");
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar />
      <div className="flex-1 p-8 overflow-y-auto">
        <h1 className="text-3xl font-bold mb-8 flex items-center gap-3">
          <span className="text-purple-400">⚡</span> Intelligence Layer Dashboard
        </h1>

        {loading ? (
          <div>Loading analytics...</div>
        ) : (
          <>
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="text-gray-400 text-sm font-medium uppercase mb-2">Total Memories</div>
                <div className="text-3xl font-bold">{stats?.total_memories}</div>
              </div>
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="text-gray-400 text-sm font-medium uppercase mb-2">Avg Confidence</div>
                <div className="text-3xl font-bold text-green-400">
                  {((stats?.avg_confidence || 0) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="text-gray-400 text-sm font-medium uppercase mb-2">Flagged Issues</div>
                <div className="text-3xl font-bold text-red-400">{stats?.flagged_executions}</div>
              </div>
              <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div className="text-gray-400 text-sm font-medium uppercase mb-2">Pending Evolutions</div>
                <div className="text-3xl font-bold text-blue-400">{stats?.pending_evolutions}</div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Recent Flagged Reflections */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <div className="p-4 border-b border-gray-700 bg-gray-800/50 flex justify-between items-center">
                  <h3 className="font-bold text-lg">Recent Issues (Self-Reflection)</h3>
                  <span className="text-xs text-red-400 bg-red-400/10 px-2 py-1 rounded">Low Confidence</span>
                </div>
                <div className="p-4 space-y-4 max-h-[400px] overflow-y-auto">
                  {reflections.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">No flagged issues found.</div>
                  ) : (
                    reflections.map((ref) => (
                      <div key={ref.id} className="bg-gray-900/50 p-4 rounded-lg border border-gray-700/50">
                        <div className="flex justify-between mb-2">
                          <span className="text-xs text-gray-500">{new Date(ref.created_at).toLocaleString()}</span>
                          <span className="text-xs font-mono text-yellow-500">
                            Confidence: {(ref.confidence_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="mb-2">
                          <span className="text-xs text-gray-400 uppercase">Critique:</span>
                          <p className="text-sm text-gray-300">{ref.critique}</p>
                        </div>
                        <div>
                          <span className="text-xs text-gray-400 uppercase">Suggestions:</span>
                          <p className="text-sm text-gray-300">{ref.suggestions}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Skill Evolutions */}
              <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                <div className="p-4 border-b border-gray-700 bg-gray-800/50 flex justify-between items-center">
                  <h3 className="font-bold text-lg">Skill Evolution Proposals</h3>
                  <span className="text-xs text-blue-400 bg-blue-400/10 px-2 py-1 rounded">Auto-Improvement</span>
                </div>
                <div className="p-4 space-y-4 max-h-[400px] overflow-y-auto">
                  {evolutions.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">No pending evolutions.</div>
                  ) : (
                    evolutions.map((evo) => (
                      <div key={evo.id} className="bg-gray-900/50 p-4 rounded-lg border border-gray-700/50">
                        <div className="flex justify-between mb-2">
                          <span className="text-xs text-gray-500">{new Date(evo.created_at).toLocaleString()}</span>
                          <span className="text-xs text-blue-400 font-bold">Pending Approval</span>
                        </div>
                        <div className="mb-3">
                          <span className="text-xs text-gray-400 uppercase">Issue Detected:</span>
                          <p className="text-sm text-red-300">{evo.issue_detected}</p>
                        </div>
                        <div className="mb-4">
                          <span className="text-xs text-gray-400 uppercase">Proposed Prompt Update:</span>
                          <div className="bg-black p-3 rounded text-xs font-mono text-green-400 overflow-x-auto mt-1">
                            {evo.proposed_prompt}
                          </div>
                        </div>
                        <button
                          onClick={() => handleApplyEvolution(evo.id)}
                          className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium transition-colors"
                        >
                          Apply Improvement
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
