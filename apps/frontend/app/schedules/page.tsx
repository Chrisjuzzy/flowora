"use client";
import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { getAgents, getSchedules, createSchedule, deleteSchedule } from '@/lib/api';
import { Agent } from '@/types';

interface Schedule {
  id: number;
  agent_id: number;
  user_id: number;
  cron_expression: string;
  is_active: boolean;
  last_run: string | null;
  next_run: string | null;
}

export default function Schedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSchedule, setNewSchedule] = useState({ agent_id: '', cron_expression: 'daily' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [schedulesData, agentsData] = await Promise.all([
        getSchedules(),
        getAgents()
      ]);
      setSchedules(schedulesData);
      setAgents(agentsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSchedule.agent_id) return;
    
    try {
      await createSchedule(Number(newSchedule.agent_id), newSchedule.cron_expression, "");
      setNewSchedule({ agent_id: '', cron_expression: 'daily' });
      fetchData();
    } catch (e) {
      alert('Failed to create schedule');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    try {
      await deleteSchedule(id);
      fetchData();
    } catch (e) {
      alert('Failed to delete schedule');
    }
  };

  const getAgentName = (id: number) => {
    return agents.find(a => a.id === id)?.name || `Agent #${id}`;
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 p-8 overflow-y-auto">
        <h1 className="text-3xl font-bold mb-8 text-gray-900">Scheduled Tasks</h1>

        {/* Create Schedule Form */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-8">
          <h2 className="text-lg font-semibold mb-4">Add New Schedule</h2>
          <form onSubmit={handleCreate} className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Agent</label>
              <select
                value={newSchedule.agent_id}
                onChange={(e) => setNewSchedule({ ...newSchedule, agent_id: e.target.value })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
                required
              >
                <option value="">Select an Agent</option>
                {agents.map(agent => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
              </select>
            </div>
            <div className="w-48">
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
              <select
                value={newSchedule.cron_expression}
                onChange={(e) => setNewSchedule({ ...newSchedule, cron_expression: e.target.value })}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="hourly">Hourly (Test)</option>
              </select>
            </div>
            <button
              type="submit"
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors font-medium"
            >
              Schedule
            </button>
          </form>
        </div>

        {/* Schedules List */}
        {loading ? (
          <div>Loading schedules...</div>
        ) : schedules.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-dashed border-gray-300 text-gray-500">
            No active schedules found.
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Agent</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Frequency</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Last Run</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Next Run</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {schedules.map((schedule) => (
                  <tr key={schedule.id} className="hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm text-gray-900 font-medium">
                      {getAgentName(schedule.agent_id)}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600 capitalize">
                      {schedule.cron_expression}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {schedule.last_run ? new Date(schedule.last_run).toLocaleString() : 'Never'}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'Pending'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDelete(schedule.id)}
                        className="text-red-600 hover:text-red-800 text-sm font-medium"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
