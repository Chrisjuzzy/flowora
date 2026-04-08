"use client";

import { useQuery } from "@tanstack/react-query";
import { executionsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export default function RunsPage() {
  const { data: executions = [] } = useQuery({ queryKey: ["executions"], queryFn: executionsApi.list });

  return (
    <div className="space-y-6">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Execution Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead>Prompt</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions.map((execution: any) => (
                <TableRow key={execution.id}>
                  <TableCell>{execution.id}</TableCell>
                  <TableCell>Agent #{execution.agent_id}</TableCell>
                  <TableCell>
                    {execution.prompt_version_id ? `v${execution.prompt_version_id}` : "-"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={execution.status === "completed" ? "accent" : "outline"}>
                      {execution.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="max-w-[360px] truncate">
                    {execution.result?.slice(0, 80)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Workflow Runs</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted">
            Workflow execution logs will appear here after you run workflows.
          </CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Swarm Runs</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted">
            Monitor swarm orchestration sessions, agents used, and completion status.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
