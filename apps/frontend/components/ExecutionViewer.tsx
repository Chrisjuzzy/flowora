import { useEffect, useState } from 'react';

export interface ExecutionResult {
  status: string;
  result: string;
  execution_id?: number;
  prompt_version_id?: number | null;
}

interface ExecutionViewerProps {
  result: ExecutionResult | null;
  onClose: () => void;
}

export default function ExecutionViewer({ result, onClose }: ExecutionViewerProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (result) setVisible(true);
  }, [result]);

  if (!visible || !result) return null;

  return (
    <div className="fixed bottom-6 right-6 w-96 bg-white shadow-2xl rounded-lg border border-gray-200 overflow-hidden transform transition-all duration-300 ease-in-out z-50">
      <div className="bg-gray-900 text-white p-4 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            result.status === 'completed' ? 'bg-green-400' : 'bg-yellow-400 animate-pulse'
          }`}></div>
          <h3 className="font-bold text-sm uppercase tracking-wide">Execution Result</h3>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
          &times;
        </button>
      </div>
      <div className="p-4 bg-gray-50 max-h-64 overflow-y-auto font-mono text-sm border-t border-gray-200">
        <div className="mb-2 text-xs text-gray-500 uppercase font-bold">Output:</div>
        <pre className="whitespace-pre-wrap text-gray-800 bg-white p-3 rounded border border-gray-200 shadow-inner">
          {result.result}
        </pre>
        <div className="mt-3 pt-3 border-t border-gray-200 flex justify-between text-xs text-gray-400">
          <span>
            ID: {result.execution_id ? `#${result.execution_id}` : "-"}
            {result.prompt_version_id ? ` · v${result.prompt_version_id}` : ""}
          </span>
          <span>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
