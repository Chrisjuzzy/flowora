"use client";
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getAgents, runAgent } from '@/lib/api';
import { Agent } from '@/types';

export default function CodeStudio() {
  const [code, setCode] = useState('// Paste your code here...');
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [helperAgent, setHelperAgent] = useState<Agent | null>(null);

  useEffect(() => {
    async function loadHelper() {
      try {
        const agents = (await getAgents()) as Agent[];
        const helper = agents.find((a) => a.name === "Code Helper Agent");
        if (helper) setHelperAgent(helper);
      } catch (e) {
        console.error("Failed to load agents", e);
      }
    }
    loadHelper();
  }, []);

  const handleAnalyze = async () => {
    if (!helperAgent) return alert("Code Helper Agent not found!");
    
    setLoading(true);
    setAnalysis("Analyzing code...");
    
    try {
      const result = await runAgent(helperAgent.id, code);
      setAnalysis(result.result);
    } catch (e) {
      setAnalysis("Error analyzing code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen">
        {/* Header */}
        <div className="bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span className="text-blue-400">&lt;/&gt;</span> Code Studio
          </h1>
          <button
            onClick={handleAnalyze}
            disabled={loading || !helperAgent}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {loading ? 'Analyzing...' : 'Analyze & Debug'}
          </button>
        </div>

        {/* Editor Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Code Input */}
          <div className="flex-1 flex flex-col border-r border-gray-700">
            <div className="bg-gray-800 px-4 py-2 text-xs text-gray-400 uppercase tracking-wider font-semibold">
              Source Code
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="flex-1 w-full bg-gray-950 text-gray-300 p-4 font-mono text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500/50 border-none"
              spellCheck={false}
            />
          </div>

          {/* Analysis Output */}
          <div className="flex-1 flex flex-col bg-gray-900">
            <div className="bg-gray-800 px-4 py-2 text-xs text-gray-400 uppercase tracking-wider font-semibold flex justify-between">
              <span>AI Analysis</span>
              {helperAgent && <span className="text-green-400 text-[10px]">{helperAgent.name} Active</span>}
            </div>
            <div className="flex-1 p-6 overflow-y-auto font-mono text-sm leading-relaxed">
              {analysis ? (
                <div className="prose prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap bg-transparent p-0 text-gray-300">
                    {analysis}
                  </pre>
                </div>
              ) : (
                <div className="text-gray-600 flex items-center justify-center h-full italic">
                  Run analysis to see feedback...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
