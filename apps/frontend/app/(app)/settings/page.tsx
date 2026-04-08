"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiKeysApi } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

type ApiKey = {
  id: number;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used?: string | null;
  api_key?: string;
};

export default function SettingsPage() {
  const [name, setName] = useState("default");
  const [newKey, setNewKey] = useState<string | null>(null);
  const { data: keys = [], refetch } = useQuery<ApiKey[]>({
    queryKey: ["api-keys"],
    queryFn: apiKeysApi.list,
  });

  const createMutation = useMutation({
    mutationFn: () => apiKeysApi.create(name),
    onSuccess: (data: ApiKey) => {
      setNewKey(data.api_key || null);
      refetch();
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: number) => apiKeysApi.revoke(id),
    onSuccess: () => refetch(),
  });

  const handleCopy = async () => {
    if (!newKey) return;
    await navigator.clipboard.writeText(newKey);
  };

  return (
    <div className="space-y-8">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">API Keys</CardTitle>
          <CardDescription>Create and manage API keys for integrations.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Key name"
              className="max-w-xs"
            />
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              Generate Key
            </Button>
          </div>
          {newKey && (
            <div className="rounded-lg border border-cyan-400/40 bg-cyan-500/10 p-4 text-sm text-cyan-100">
              <div className="flex items-center justify-between">
                <span>New API Key (store it now)</span>
                <Button size="sm" variant="outline" onClick={handleCopy}>
                  Copy
                </Button>
              </div>
              <code className="mt-2 block break-all text-xs">{newKey}</code>
            </div>
          )}
          <div className="space-y-3">
            {keys.map((key) => (
              <div
                key={key.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-surface-2/60 p-4 text-sm"
              >
                <div>
                  <p className="font-semibold text-white">{key.name}</p>
                  <p className="text-xs text-muted">Prefix: {key.key_prefix}</p>
                  <p className="text-xs text-muted">
                    Created {new Date(key.created_at).toLocaleString()}
                  </p>
                  {key.last_used && (
                    <p className="text-xs text-muted">
                      Last used {new Date(key.last_used).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="outline">{key.is_active ? "Active" : "Revoked"}</Badge>
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={!key.is_active || revokeMutation.isPending}
                    onClick={() => revokeMutation.mutate(key.id)}
                  >
                    Revoke
                  </Button>
                </div>
              </div>
            ))}
            {!keys.length && <div className="text-sm text-muted">No API keys created yet.</div>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
