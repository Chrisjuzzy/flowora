"use client";
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getWorkflow, runWorkflow } from '@/lib/api';
import { Workflow } from '@/types';
import FloworaLoader from '@/components/FloworaLoader';

interface WorkflowResult {
    workflow_id: number;
    status: string;
    steps_results: {
        step: number;
        agent_id: number;
        status: string;
        result: string;
        error?: string;
    }[];
    final_output: string;
}

export default function WorkflowDetail() {
    const params = useParams();
    const id = parseInt(params.id as string);
    const [workflow, setWorkflow] = useState<Workflow | null>(null);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [inputData, setInputData] = useState('');
    const [result, setResult] = useState<WorkflowResult | null>(null);

    useEffect(() => {
        async function load() {
            if (!id) return;
            try {
                const data = await getWorkflow(id);
                setWorkflow(data);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [id]);

    const handleRun = async () => {
        if (!workflow) return;
        setRunning(true);
        setResult(null);
        try {
            const res = await runWorkflow(workflow.id, inputData);
            setResult(res);
        } catch (e) {
            console.error(e);
            alert('Workflow execution failed');
        } finally {
            setRunning(false);
        }
    };

    if (loading) return <div>Loading...</div>;
    if (!workflow) return <div>Workflow not found</div>;

    return (
            <div className="space-y-6">
                <FloworaLoader show={running} />
                <div className="flex justify-between items-center">
                    <h1 className="text-3xl font-bold">{workflow.name}</h1>
                    <button
                        onClick={handleRun}
                        disabled={running}
                        className="px-6 py-2 bg-accent text-black rounded-md hover:bg-amber-300 disabled:opacity-50 font-medium shadow-sm transition-colors"
                    >
                        {running ? 'Running...' : 'Run Workflow'}
                    </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Input Section */}
                    <div className="app-surface p-6 rounded-lg">
                        <h2 className="text-xl font-bold mb-4">Configuration</h2>
                        <div className="mb-4">
                            <label className="block text-muted font-bold mb-2">Initial Input</label>
                            <textarea
                                value={inputData}
                                onChange={(e) => setInputData(e.target.value)}
                                className="w-full p-3 border border-border rounded bg-surface-2/60 text-white h-32"
                                placeholder="Enter initial input for the first agent..."
                            />
                        </div>
                        
                        <h3 className="font-bold text-muted mb-2">Steps</h3>
                        <div className="space-y-2">
                            {workflow.config_json.steps.map((step, index) => (
                                <div key={index} className="flex items-center space-x-3 p-3 bg-surface-2/60 rounded border border-border">
                                    <span className="bg-surface text-muted text-xs font-bold px-2 py-1 rounded-full">{index + 1}</span>
                                    <span className="font-medium">{step.step_name}</span>
                                    <span className="text-muted text-sm">(Agent ID: {step.agent_id})</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Result Section */}
                    <div className="app-surface p-6 rounded-lg">
                        <h2 className="text-xl font-bold mb-4">Execution Result</h2>
                        {result ? (
                            <div className="space-y-6">
                                <div className={`p-4 rounded-md border ${result.status === 'completed' ? 'bg-green-500/10 border-green-500/40 text-green-300' : 'bg-red-500/10 border-red-500/40 text-red-300'}`}>
                                    <span className="font-bold">Status:</span> {result.status}
                                </div>
                                
                                <div>
                                    <h3 className="font-bold text-muted mb-2">Step Results</h3>
                                    <div className="space-y-4">
                                        {result.steps_results.map((stepRes, idx) => (
                                            <div key={idx} className="border border-border rounded p-3">
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className="font-bold text-sm text-muted">Step {stepRes.step + 1}</span>
                                                    <span className={`text-xs px-2 py-1 rounded-full ${stepRes.status === 'completed' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
                                                        {stepRes.status}
                                                    </span>
                                                </div>
                                                <pre className="text-xs bg-surface-2/60 p-2 rounded overflow-x-auto whitespace-pre-wrap text-white">
                                                    {stepRes.result || stepRes.error}
                                                </pre>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div>
                                    <h3 className="font-bold text-muted mb-2">Final Output</h3>
                                    <pre className="bg-black/70 text-gray-100 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap text-sm shadow-inner">
                                        {result.final_output}
                                    </pre>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-12 text-muted italic">
                                Run the workflow to see results here.
                            </div>
                        )}
                    </div>
                </div>
            </div>
    );
}
