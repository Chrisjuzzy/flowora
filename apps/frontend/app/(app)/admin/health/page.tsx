'use client';

import { useState, useEffect } from 'react';
import { getHealthStatus } from '@/lib/api';

export default function HealthDashboard() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchHealth = async () => {
    try {
      const data = await getHealthStatus();
      setHealth(data);
    } catch (error) {
      console.error('Failed to load health status:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
      <main className="space-y-6">
        <h1 className="text-3xl font-bold">System Health Monitor</h1>

        {loading && <div className="text-center">Loading status...</div>}

        {health && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-surface-2/60 p-6 rounded-lg border border-border">
              <h3 className="text-muted text-sm font-bold uppercase mb-2">Status</h3>
              <div className={`text-2xl font-bold ${health.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                {health.status}
              </div>
            </div>

            <div className="bg-surface-2/60 p-6 rounded-lg border border-border">
              <h3 className="text-muted text-sm font-bold uppercase mb-2">Database</h3>
              <div className="text-2xl font-bold text-blue-300">{health.database}</div>
            </div>

            <div className="bg-surface-2/60 p-6 rounded-lg border border-border">
              <h3 className="text-muted text-sm font-bold uppercase mb-2">Redis</h3>
              <div className="text-2xl font-bold text-purple-300">{health.redis}</div>
            </div>

            <div className="bg-surface-2/60 p-6 rounded-lg border border-border">
              <h3 className="text-muted text-sm font-bold uppercase mb-2">Celery</h3>
              <div className="text-2xl font-bold text-yellow-300">{health.celery}</div>
            </div>
          </div>
        )}

        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h3 className="text-xl font-bold mb-4">Recent Logs</h3>
          <div className="bg-black p-4 rounded text-sm font-mono text-green-400 h-64 overflow-y-auto">
            {/* Mock logs for now */}
            <div>[INFO] System started at {new Date().toISOString()}</div>
            <div>[INFO] Health check passed</div>
            <div>[INFO] Database connection verified</div>
            <div>[WARN] High CPU usage detected (simulated)</div>
          </div>
        </div>
      </main>
  );
}
