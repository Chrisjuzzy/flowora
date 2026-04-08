import { useState } from 'react';
import { runAgent } from '@/lib/api';
import { Agent } from '@/types';
import { ExecutionResult } from '@/components/ExecutionViewer';

interface RunAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  agent: Agent | null;
  onSuccess: (result: ExecutionResult) => void;
}

export default function RunAgentModal({ isOpen, onClose, agent, onSuccess }: RunAgentModalProps) {
  const [inputData, setInputData] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !agent) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await runAgent(agent.id, inputData);
      onSuccess(result);
      onClose();
      setInputData('');
    } catch (error) {
      console.error(error);
      setError(error instanceof Error ? error.message : 'Failed to run agent');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-8 rounded-lg w-full max-w-md shadow-2xl">
        <h2 className="text-2xl font-bold mb-4 text-gray-900">Run {agent.name}</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">Input Data (Optional)</label>
            <textarea
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              rows={4}
              placeholder="Enter input for the agent (e.g. URL, code snippet, text)..."
            />
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </div>
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 font-medium shadow-sm transition-colors"
            >
              {loading ? 'Running...' : 'Run Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
