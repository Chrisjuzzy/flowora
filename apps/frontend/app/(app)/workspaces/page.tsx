"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { workspacesApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState } from "react";

export default function WorkspacesPage() {
  const { data: workspaces = [], refetch } = useQuery({
    queryKey: ["workspaces"],
    queryFn: workspacesApi.list,
  });
  const [name, setName] = useState("");

  const createMutation = useMutation({
    mutationFn: () => workspacesApi.create({ name, type: "business" }),
    onSuccess: () => {
      setName("");
      refetch();
    },
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Workspaces</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {workspaces.map((workspace: any) => (
            <div
              key={workspace.id}
              className="rounded-lg border border-border/60 bg-surface-2/60 p-4"
            >
              <p className="font-semibold">{workspace.name}</p>
              <p className="text-xs text-muted">Owner #{workspace.owner_id}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Create Workspace</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Workspace name" />
          <Button className="w-full" onClick={() => createMutation.mutate()} disabled={!name}>
            Create Workspace
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
