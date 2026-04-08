import { Agent } from '@/types';
import Link from 'next/link';

interface AgentCardProps {
  agent: Agent;
  onRun: (id: number) => void;
  onClone?: (id: number) => void;
  onEdit?: (agent: Agent) => void;
}

export default function AgentCard({ agent, onRun, onClone, onEdit }: AgentCardProps) {
  const isSystem = !agent.owner_id;

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <Link href={`/agents/manage/${agent.id}`} className="hover:underline">
            <h3 className="text-xl font-semibold text-gray-900">{agent.name}</h3>
          </Link>
          {isSystem && (
            <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full mt-1 inline-block">
              System Template
            </span>
          )}
        </div>
        {!isSystem && (
          <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
            Active
          </span>
        )}
      </div>
      <p className="text-gray-600 mb-6 h-12 overflow-hidden line-clamp-2">
        {agent.description || 'No description provided.'}
      </p>
      <div className="flex justify-between items-center pt-4 border-t border-gray-100">
        <span className="text-xs text-gray-500">ID: #{agent.id}</span>
        <div className="flex space-x-2">
          <Link href={`/agents/manage/${agent.id}`}>
            <button className="bg-gray-100 text-gray-700 px-3 py-2 rounded-md hover:bg-gray-200 transition-colors text-sm font-medium border border-gray-300">
              Details
            </button>
          </Link>
          {!isSystem && onEdit && (
            <button
              onClick={() => onEdit(agent)}
              className="bg-gray-100 text-gray-700 px-3 py-2 rounded-md hover:bg-gray-200 transition-colors text-sm font-medium border border-gray-300"
            >
              Edit
            </button>
          )}
          {isSystem && onClone && (
            <button
              onClick={() => onClone(agent.id)}
              className="bg-gray-100 text-gray-700 px-3 py-2 rounded-md hover:bg-gray-200 transition-colors text-sm font-medium border border-gray-300"
            >
              Clone
            </button>
          )}
          <button
            onClick={() => onRun(agent.id)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            Run
          </button>
        </div>
      </div>
    </div>
  );
}
