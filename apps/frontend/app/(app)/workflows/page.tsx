"use client";

import { useCallback, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { workflowsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Workflow, Code, Database, Timer, PlugZap, GitBranch } from "lucide-react";

const nodePalette = [
  { type: "agent", label: "Agent Node", icon: Workflow },
  { type: "api", label: "API Node", icon: PlugZap },
  { type: "logic", label: "Logic Node", icon: Code },
  { type: "condition", label: "Condition Node", icon: GitBranch },
  { type: "delay", label: "Delay Node", icon: Timer },
  { type: "webhook", label: "Webhook Node", icon: Database },
];

const initialNodes = [
  {
    id: "start",
    position: { x: 50, y: 60 },
    data: { label: "Trigger" },
    type: "input",
  },
];

const initialEdges: any[] = [];

export default function WorkflowBuilderPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [workflowName, setWorkflowName] = useState("New Workflow");

  const saveMutation = useMutation({
    mutationFn: () =>
      workflowsApi.create({
        name: workflowName,
        config_json: {
          nodes,
          edges,
        },
      }),
  });

  const onConnect = useCallback(
    (params: any) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData("application/reactflow");
      if (!type) return;
      const position = { x: event.clientX - 420, y: event.clientY - 220 };
      const newNode = {
        id: `${type}-${nodes.length + 1}`,
        position,
        data: { label: `${type} node`.toUpperCase() },
        type: "default",
      };
      setNodes((nds) => nds.concat(newNode));
    },
    [nodes.length, setNodes]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Workflow Builder</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={workflowName} onChange={(e) => setWorkflowName(e.target.value)} />
          <div className="space-y-3">
            {nodePalette.map((node) => {
              const Icon = node.icon;
              return (
                <div
                  key={node.type}
                  className="flex cursor-grab items-center justify-between rounded-lg border border-border/60 bg-surface-2/60 p-3"
                  draggable
                  onDragStart={(event) =>
                    event.dataTransfer.setData("application/reactflow", node.type)
                  }
                >
                  <div className="flex items-center gap-2 text-sm">
                    <Icon size={16} />
                    {node.label}
                  </div>
                  <Badge variant="outline">Node</Badge>
                </div>
              );
            })}
          </div>
          <Button className="w-full" onClick={() => saveMutation.mutate()}>
            Save Workflow
          </Button>
        </CardContent>
      </Card>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Canvas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[620px] rounded-xl border border-border/60 bg-surface-2/40">
            <ReactFlowProvider>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onDrop={onDrop}
                onDragOver={onDragOver}
                fitView
              >
                <Background gap={16} size={1} />
                <MiniMap />
                <Controls />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
