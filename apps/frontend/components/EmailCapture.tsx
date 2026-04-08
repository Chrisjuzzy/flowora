"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function EmailCapture({ label = "Get early access to powerful AI agents." }: { label?: string }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!email) return;
    setStatus("Thanks! You're on the Flowora waitlist.");
    setEmail("");
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-border bg-surface-2/60 p-4">
      <p className="text-sm text-muted">{label}</p>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
        />
        <Button type="submit">Join Waitlist</Button>
      </div>
      {status && <p className="mt-2 text-xs text-muted">{status}</p>}
    </form>
  );
}
