"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FloworaIcon } from "@/components/FloworaBrand";

export default function VerifyEmailClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") || "";
  const [email, setEmail] = useState(searchParams.get("email") || "");
  const [status, setStatus] = useState<"idle" | "verifying" | "verified" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    const verify = async () => {
      setStatus("verifying");
      setMessage(null);
      try {
        const res = await authApi.verifyEmailToken(token);
        setStatus("verified");
        setMessage(res?.message || `Email verified for ${res?.email || "your account"}.`);
      } catch (err: any) {
        setStatus("error");
        setMessage(err.message || "Verification failed.");
      }
    };
    verify();
  }, [token]);

  const handleResend = async () => {
    if (!email) {
      setMessage("Please enter your email to resend the verification link.");
      setStatus("error");
      return;
    }
    setStatus("verifying");
    setMessage(null);
    try {
      const res = await authApi.resendVerificationEmail(email);
      setStatus("idle");
      setMessage(res?.message || "Verification link sent.");
    } catch (err: any) {
      setStatus("error");
      setMessage(err.message || "Failed to resend verification email.");
    }
  };

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-lg flex-col justify-center px-6 py-12">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <FloworaIcon size={72} />
        <h1 className="text-3xl font-semibold heading-serif">Verify your email</h1>
        <p className="text-sm text-muted">Where AI Agents Flow Together</p>
      </div>

      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Email verification</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted">
            {token
              ? "We are verifying your email now. If it fails, resend a new link below."
              : "Enter your email to resend a verification link."}
          </p>

          {!token && (
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
            />
          )}

          {message && (
            <div
              className={`rounded-lg border px-3 py-2 text-sm ${
                status === "error" ? "border-red-500/50 text-red-300" : "border-border/60 text-muted"
              }`}
            >
              {message}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button onClick={handleResend} disabled={status === "verifying"}>
              Resend verification email
            </Button>
            <Button variant="outline" onClick={() => router.push("/login")}>
              Back to login
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
