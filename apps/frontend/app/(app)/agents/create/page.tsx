"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createAgent } from '@/lib/api';

export default function CreateAgent() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await createAgent(name, description, { system_prompt: systemPrompt });
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Failed to create agent', err);
      setError(err.message || 'Failed to create agent');
    } finally {
      setLoading(false);
    }
  };

  return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Create New Agent</h1>
        
        {error && (
          <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="max-w-2xl app-surface p-8 rounded-lg">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-muted mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full p-3 border border-border rounded bg-surface-2/60 text-white"
                placeholder="My Awesome Agent"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-muted mb-1">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full p-3 border border-border rounded bg-surface-2/60 text-white"
                placeholder="What does this agent do?"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-muted mb-1">System Prompt</label>
              <p className="text-xs text-muted mb-2">Define the agent's persona and instructions.</p>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={6}
                className="w-full p-3 border border-border rounded bg-surface-2/60 text-white font-mono text-sm"
                placeholder="You are a helpful assistant..."
              />
            </div>

            <div className="flex justify-end pt-4 border-t border-border">
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
                {loading ? 'Creating...' : 'Create Agent'}
              </button>
            </div>
          </div>
        </form>
      </div>
  );
}
