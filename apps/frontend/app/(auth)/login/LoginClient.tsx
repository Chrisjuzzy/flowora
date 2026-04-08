"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FloworaIcon } from "@/components/FloworaBrand";

export default function LoginClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useAuthStore((state) => state.setSession);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [welcome, setWelcome] = useState(false);

  useEffect(() => {
    const flag = searchParams.get("welcome") === "1" || localStorage.getItem("flowora_show_templates") === "1";
    setWelcome(flag);
  }, [searchParams]);

  const handleLogin = async () => {
    try {
      setError(null);
      const data = await authApi.login(email, password);
      setSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: { email, role: data.role },
      });
      if (welcome) {
        localStorage.removeItem("flowora_show_templates");
        router.push("/templates?welcome=1");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-8 text-center">
      <div className="space-y-3">
        <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-3xl border border-border bg-surface-2/70">
          <FloworaIcon size={96} />
        </div>
        <h1 className="text-3xl font-semibold heading-serif">Flowora</h1>
        <p className="text-sm text-muted">Where AI Agents Flow Together</p>
      </div>

      <Card className="app-surface text-left">
        <CardHeader>
          <CardTitle className="heading-serif">Sign in</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {welcome && (
            <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-xs text-muted">
              Welcome to Flowora - sign in to access starter templates.
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
          <Button className="w-full" onClick={handleLogin}>
            Login
          </Button>
          <p className="text-xs text-muted">
            Use your backend credentials.{" "}
            <a href="/register" className="text-white underline">
              Create an account
            </a>
            .
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
