import { useState, useEffect } from 'react';
import { updateAgent } from '@/lib/api';
import { Agent } from '@/types';

interface EditAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  agent: Agent | null;
}

export default function EditAgentModal({ isOpen, onClose, onSuccess, agent }: EditAgentModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [config, setConfig] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (agent) {
      setName(agent.name);
      setDescription(agent.description || '');
      setConfig(agent.config ? JSON.stringify(agent.config, null, 2) : '{}');
    }
  }, [agent]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agent) return;

    setLoading(true);
    try {
      let parsedConfig = {};
      try {
        parsedConfig = JSON.parse(config);
      } catch (e) {
        alert('Invalid JSON config');
        setLoading(false);
        return;
      }

      await updateAgent(agent.id, { name, description, config: parsedConfig });
      onSuccess();
      onClose();
    } catch (error) {
      console.error(error);
      alert('Failed to update agent');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !agent) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-8 rounded-lg w-full max-w-lg shadow-2xl">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Edit Agent</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              rows={2}
            />
          </div>
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">Config (JSON)</label>
            <textarea
              value={config}
              onChange={(e) => setConfig(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all font-mono text-sm"
              rows={6}
            />
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
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
