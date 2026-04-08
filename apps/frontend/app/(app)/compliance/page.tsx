"use client";

import { useMutation } from "@tanstack/react-query";
import { complianceApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useState } from "react";

export default function CompliancePage() {
  const [target, setTarget] = useState("api.example.com");
  const [scanType, setScanType] = useState("quick");
  const scanMutation = useMutation({
    mutationFn: () => complianceApi.scan({ target, scan_type: scanType }),
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[1.2fr_1fr]">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Compliance Scans</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Target URL or IP" />
          <Select value={scanType} onChange={(e) => setScanType(e.target.value)}>
            <option value="quick">Quick Scan</option>
            <option value="full">Full Scan</option>
            <option value="custom">Custom Scan</option>
          </Select>
          <Button onClick={() => scanMutation.mutate()}>Run Scan</Button>
          {scanMutation.data && (
            <div className="rounded-lg border border-border/60 bg-surface-2/60 p-4 text-sm text-muted">
              Scan complete. Vulnerabilities: {scanMutation.data.vulnerabilities?.length || 0}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Compliance History</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted">
          Compliance scans, remediation guidance, and audit trails will appear here.
        </CardContent>
      </Card>
    </div>
  );
}
