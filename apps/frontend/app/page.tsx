"use client";

import Link from "next/link";
import { FloworaIcon } from "@/components/FloworaBrand";
import { Button } from "@/components/ui/button";
import EmailCapture from "@/components/EmailCapture";

const features = [
  {
    title: "Agent Studio",
    description: "Design agents with prompts, tools, memory, and guardrails in minutes.",
  },
  {
    title: "Visual Workflows",
    description: "Connect agents with React Flow to orchestrate complex automations.",
  },
  {
    title: "Marketplace",
    description: "Publish, install, and clone agents with built-in monetization.",
  },
  {
    title: "Observability",
    description: "Track execution latency, queue depth, and usage in Grafana.",
  },
];

const steps = [
  {
    title: "Build",
    description: "Create agents with prompts, tools, and memory strategies.",
  },
  {
    title: "Deploy",
    description: "Launch agents into workflows, schedules, and the marketplace.",
  },
  {
    title: "Scale",
    description: "Monitor performance and scale with Celery + Redis.",
  },
];

const pricing = [
  { name: "Starter", price: "$29", detail: "For solo builders", perks: "10 agents • 5 workflows" },
  { name: "Growth", price: "$99", detail: "For growing teams", perks: "Unlimited agents • 25 workflows" },
  { name: "Enterprise", price: "Custom", detail: "For large orgs", perks: "SLA • Dedicated cluster" },
];

const faqs = [
  {
    q: "Can I run Flowora locally?",
    a: "Yes. Use Docker Compose to spin up the full stack in minutes.",
  },
  {
    q: "Does Flowora support custom models?",
    a: "Yes. Bring your own provider or run locally with Ollama.",
  },
  {
    q: "Is the marketplace optional?",
    a: "It’s modular. You can disable marketplace features in config.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-24 px-6 py-16 lg:px-12">
      <section className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Flowora</p>
          <h1 className="text-4xl font-semibold leading-tight heading-serif sm:text-5xl">
            Build AI Agents That Work For You
          </h1>
          <p className="text-lg text-muted">
            Design, run, and scale AI agents with visual workflows. Flowora unifies execution, marketplace
            distribution, and observability in one platform.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/dashboard">
              <Button>Start Building</Button>
            </Link>
            <Link href="/marketplace">
              <Button variant="outline">View Marketplace</Button>
            </Link>
            <Link href="/demo">
              <Button variant="secondary">Try Demo</Button>
            </Link>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="rounded-full border border-border px-3 py-1">FastAPI + Next.js 14</span>
            <span className="rounded-full border border-border px-3 py-1">Celery + Redis</span>
            <span className="rounded-full border border-border px-3 py-1">pgvector</span>
          </div>
        </div>
        <div className="relative">
          <div className="absolute -inset-6 rounded-3xl bg-gradient-to-br from-blue-500/20 via-yellow-400/10 to-transparent blur-2xl" />
          <div className="relative rounded-3xl border border-border bg-surface-2/70 p-8">
            <div className="flex items-center gap-3">
              <FloworaIcon size={56} />
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-muted">Flowora</p>
                <p className="text-lg font-semibold">Where AI Agents Flow Together</p>
              </div>
            </div>
            <div className="mt-6 space-y-4 text-sm text-muted">
              <p>Orchestrate agents, workflows, and revenue streams in one console.</p>
              <div className="rounded-xl border border-border bg-black/30 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-muted">Live Status</p>
                <p className="mt-2 text-sm text-white">All systems operational • 24 agents running</p>
              </div>
              <div className="grid gap-2 text-xs text-muted">
                <span>Agent latency: 1.4s avg</span>
                <span>Queue depth: 12 tasks</span>
                <span>Marketplace installs: 3.2k</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl space-y-8">
        <div>
          <h2 className="text-3xl font-semibold heading-serif">Features</h2>
          <p className="mt-2 text-muted">Everything you need to ship AI agents in production.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {features.map((feature) => (
            <div key={feature.title} className="rounded-2xl border border-border bg-surface-2/60 p-6">
              <h3 className="text-xl font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm text-muted">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl space-y-8">
        <div>
          <h2 className="text-3xl font-semibold heading-serif">How it works</h2>
          <p className="mt-2 text-muted">From prompt to production in three steps.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {steps.map((step, idx) => (
            <div key={step.title} className="rounded-2xl border border-border bg-surface-2/60 p-6">
              <p className="text-xs uppercase tracking-[0.3em] text-muted">Step {idx + 1}</p>
              <h3 className="mt-2 text-xl font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-muted">{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl space-y-8">
        <div>
          <h2 className="text-3xl font-semibold heading-serif">Agent Marketplace</h2>
          <p className="mt-2 text-muted">Discover, install, and clone top-performing agents.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {["Startup Idea Generator", "Marketing Copy Agent", "Blog Writer"].map((agent) => (
            <div key={agent} className="rounded-2xl border border-border bg-surface-2/60 p-6">
              <h3 className="text-lg font-semibold">{agent}</h3>
              <p className="mt-2 text-sm text-muted">Pre-built agent ready to install.</p>
              <Link href="/marketplace" className="mt-4 inline-block text-xs text-muted hover:text-white">
                Explore marketplace →
              </Link>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl space-y-8">
        <div>
          <h2 className="text-3xl font-semibold heading-serif">Pricing</h2>
          <p className="mt-2 text-muted">Choose the plan that matches your scale.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {pricing.map((plan) => (
            <div key={plan.name} className="rounded-2xl border border-border bg-surface-2/60 p-6">
              <h3 className="text-lg font-semibold">{plan.name}</h3>
              <p className="mt-2 text-3xl font-semibold">{plan.price}</p>
              <p className="mt-2 text-sm text-muted">{plan.detail}</p>
              <p className="mt-4 text-xs text-muted">{plan.perks}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl space-y-6">
        <h2 className="text-3xl font-semibold heading-serif">FAQ</h2>
        <div className="grid gap-4">
          {faqs.map((faq) => (
            <div key={faq.q} className="rounded-2xl border border-border bg-surface-2/60 p-5">
              <p className="font-semibold">{faq.q}</p>
              <p className="mt-2 text-sm text-muted">{faq.a}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-3xl">
        <EmailCapture />
      </section>
    </div>
  );
}
