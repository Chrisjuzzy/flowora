"use client";

import SeoLandingPage from "@/components/SeoLandingPage";

export default function AIWorkflowBuilderPage() {
  return (
    <SeoLandingPage
      title="AI Workflow Builder"
      headline="Visual AI Workflow Builder with Flowora"
      benefits={[
        "Connect agents and tools with a drag-and-drop canvas.",
        "Run multi-step automations with guardrails and observability.",
        "Scale workloads with Celery, Redis, and pgvector memory.",
      ]}
    />
  );
}
