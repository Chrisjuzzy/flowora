"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FloworaIcon } from "@/components/FloworaBrand";

export default function RegisterClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [referralCode, setReferralCode] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("ref") || localStorage.getItem("flowora_referral_code");
    if (code) {
      setReferralCode(code);
    }
  }, [searchParams]);

  const handleRegister = async () => {
    try {
      setError(null);
      await authApi.register(email, password, referralCode || undefined);
      localStorage.setItem("flowora_show_templates", "1");
      router.push(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-8 text-center">
      <div className="space-y-3">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl border border-border bg-surface-2/70">
          <FloworaIcon size={80} />
        </div>
        <h1 className="text-2xl font-semibold heading-serif">Create your Flowora account</h1>
        <p className="text-sm text-muted">Where AI Agents Flow Together</p>
      </div>

      <Card className="app-surface text-left">
        <CardHeader>
          <CardTitle className="heading-serif">Create account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {referralCode && (
            <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-xs text-muted">
              Referral applied: {referralCode}
            </div>
          )}
          <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button className="w-full" onClick={handleRegister}>
            Register
          </Button>
          <p className="text-xs text-muted">
            Already have an account?{" "}
            <a href="/login" className="text-white underline">
              Sign in
            </a>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
