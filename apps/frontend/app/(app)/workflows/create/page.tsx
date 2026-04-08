"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAgents, createWorkflow } from '@/lib/api';
import { Agent } from '@/types';

export default function CreateWorkflow() {
  const [name, setName] = useState('');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [steps, setSteps] = useState<{agent_id: number, step_name: string}[]>([]);
  const [loading, setLoading] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [jsonInput, setJsonInput] = useState('');
  const router = useRouter();

  useEffect(() => {
    async function loadAgents() {
      try {
        const data = await getAgents();
        setAgents(data);
      } catch (e) {
        console.error('Failed to load agents', e);
      }
    }
    loadAgents();
  }, []);

  const addStep = () => {
    if (agents.length === 0) return;
    setSteps([...steps, { agent_id: agents[0].id, step_name: `Step ${steps.length + 1}` }]);
  };

  const updateStep = (index: number, field: string, value: any) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    setSteps(newSteps);
  };

  const removeStep = (index: number) => {
    const newSteps = steps.filter((_, i) => i !== index);
    setSteps(newSteps);
  };

  const handleImport = () => {
    try {
      const data = JSON.parse(jsonInput);
      if (data.name) setName(data.name);
      if (Array.isArray(data.steps)) {
        setSteps(data.steps);
      }
      setShowImport(false);
    } catch (e) {
      alert('Invalid JSON');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || steps.length === 0) return;
    
    setLoading(true);
    try {
      await createWorkflow(name, { steps });
      router.push('/workflows');
    } catch (e) {
      console.error(e);
      alert('Failed to create workflow');
    } finally {
      setLoading(false);
    }
  };

  return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold">Create Workflow</h1>
            <button 
                onClick={() => setShowImport(!showImport)}
                className="text-sm text-muted hover:text-white font-medium"
            >
                {showImport ? 'Hide Import' : 'Import from JSON'}
            </button>
        </div>
        
        {showImport && (
            <div className="mb-8 bg-surface-2/60 p-6 rounded-lg border border-border">
                <label className="block text-sm font-bold text-muted mb-2">
                    Paste Workflow Configuration (from Workflow Builder Agent)
                </label>
                <textarea
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    className="w-full h-32 p-3 text-sm font-mono border border-border rounded bg-surface-2/60 text-white mb-4"
                    placeholder='{"name": "My Workflow", "steps": [{"agent_id": 1, "step_name": "Step 1"}]}'
                />
                <button
                    onClick={handleImport}
                    className="px-4 py-2 bg-accent text-black text-sm font-medium rounded hover:bg-amber-300"
                >
                    Load Configuration
                </button>
            </div>
        )}

        <form onSubmit={handleSubmit} className="max-w-2xl app-surface p-8 rounded-lg">
          <div className="mb-6">
            <label className="block text-muted font-bold mb-2">Workflow Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-3 border border-border rounded bg-surface-2/60 text-white"
              placeholder="e.g., Content Generation Pipeline"
              required
            />
          </div>

          <div className="mb-6">
            <div className="flex justify-between items-center mb-4">
              <label className="block text-muted font-bold">Steps</label>
              <button
                type="button"
                onClick={addStep}
                className="text-sm text-muted hover:text-white font-medium"
              >
                + Add Step
              </button>
            </div>
            
            {steps.length === 0 ? (
              <div className="text-center py-8 bg-surface-2/40 rounded border border-dashed border-border text-muted">
                No steps added. Add an agent to start.
              </div>
            ) : (
              <div className="space-y-4">
                {steps.map((step, index) => (
                  <div key={index} className="flex items-center space-x-4 p-4 bg-surface-2/60 rounded border border-border">
                    <span className="font-bold text-muted w-6">{index + 1}.</span>
                    <input
                      type="text"
                      value={step.step_name}
                      onChange={(e) => updateStep(index, 'step_name', e.target.value)}
                      className="flex-1 p-2 border border-border rounded bg-surface-2/60 text-white"
                      placeholder="Step Name"
                      required
                    />
                    <select
                      value={step.agent_id}
                      onChange={(e) => updateStep(index, 'agent_id', parseInt(e.target.value))}
                      className="flex-1 p-2 border border-border rounded bg-surface-2/60 text-white"
                    >
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => removeStep(index)}
                      className="text-red-400 hover:text-red-300 font-medium text-sm px-2"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end pt-6 border-t border-border">
            <button
              type="button"
              onClick={() => router.back()}
              className="mr-4 px-4 py-2 text-muted hover:text-white font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-accent text-black rounded-md hover:bg-amber-300 disabled:opacity-50 font-medium shadow-sm transition-colors"
            >
              {loading ? 'Creating...' : 'Create Workflow'}
            </button>
          </div>
        </form>
      </div>
  );
}
