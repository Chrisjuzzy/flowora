"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import EmailCapture from "@/components/EmailCapture";
import { FloworaLogo } from "@/components/FloworaBrand";

type SeoLandingProps = {
  title: string;
  headline: string;
  benefits: string[];
  ctaPrimary?: string;
  ctaSecondary?: string;
};

export default function SeoLandingPage({
  title,
  headline,
  benefits,
  ctaPrimary = "Start Building",
  ctaSecondary = "View Marketplace",
}: SeoLandingProps) {
  return (
    <div className="mx-auto max-w-5xl space-y-12 px-6 py-16">
      <section className="space-y-6">
        <p className="text-xs uppercase tracking-[0.3em] text-muted">Flowora</p>
        <h1 className="text-4xl font-semibold heading-serif">{headline}</h1>
        <p className="text-muted">
          {title} powered by Flowora - the AI workflow platform where agents, data, and execution flow together.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/dashboard">
            <Button>{ctaPrimary}</Button>
          </Link>
          <Link href="/marketplace">
            <Button variant="outline">{ctaSecondary}</Button>
          </Link>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-2xl border border-border bg-surface-2/60 p-6">
          <h2 className="text-xl font-semibold">Benefits</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted">
            {benefits.map((benefit) => (
              <li key={benefit}>- {benefit}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-2xl border border-border bg-surface-2/60 p-6">
          <h2 className="text-xl font-semibold">Screenshots</h2>
          <div className="mt-4 grid gap-3">
            <div className="rounded-xl border border-border bg-black/40 p-4">
              <FloworaLogo width={420} height={240} className="rounded-lg" label="Flowora UI" />
              <p className="mt-2 text-xs text-muted">Agent studio preview</p>
            </div>
            <div className="rounded-xl border border-border bg-black/40 p-4">
              <FloworaLogo width={420} height={240} className="rounded-lg" label="Flowora analytics" />
              <p className="mt-2 text-xs text-muted">Workflow and analytics preview</p>
            </div>
          </div>
        </div>
      </section>

      <EmailCapture />
    </div>
  );
}
