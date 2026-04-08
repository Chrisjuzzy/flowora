"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { templatesApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface TemplateItem {
  id: number;
  name: string;
  description?: string;
  category?: string;
  tags?: string;
  base_config?: Record<string, any>;
  slug: string;
  install_count?: number;
  share_count?: number;
  creator?: { id: number; email: string } | null;
}

export default function TemplateDetailClient({ slug }: { slug: string }) {
  const [template, setTemplate] = useState<TemplateItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [installing, setInstalling] = useState(false);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    const loadTemplate = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await templatesApi.getBySlug(slug);
        setTemplate(data);
      } catch (err: any) {
        setError(err?.message || "Template not found.");
      } finally {
        setLoading(false);
      }
    };
    loadTemplate();
  }, [slug]);

  const handleInstall = async () => {
    if (!template) return;
    setInstalling(true);
    setMessage(null);
    try {
      const response = await templatesApi.install(template.id);
      setMessage("Template installed to your workspace.");
      setTemplate((prev) =>
        prev ? { ...prev, install_count: response.install_count } : prev
      );
    } catch (err: any) {
      setMessage(err?.message || "Install failed.");
    } finally {
      setInstalling(false);
    }
  };

  const handleShare = async () => {
    if (!template) return;
    setSharing(true);
    setMessage(null);
    try {
      const url = `${window.location.origin}/templates/${template.slug}`;
      if (navigator.share) {
        await navigator.share({ title: template.name, text: template.description || "", url });
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
      }
      await templatesApi.share(template.id);
      setMessage("Share link ready. Paste it anywhere to spread Flowora.");
    } catch (err: any) {
      setMessage(err?.message || "Share failed.");
    } finally {
      setSharing(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-sm text-muted">Loading template...</div>;
  }

  if (error || !template) {
    return (
      <div className="p-8">
        <p className="text-sm text-red-200">{error || "Template not found."}</p>
        <Link href="/templates" className="mt-4 inline-block text-sm text-accent">
          Back to templates
        </Link>
      </div>
    );
  }

  const tags = template.tags
    ? template.tags.split(",").map((tag) => tag.trim()).filter(Boolean)
    : [];

  return (
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto max-w-3xl">
        <Link href="/templates" className="text-sm text-accent">
          ← Back to templates
        </Link>
        <div className="mt-6 rounded-3xl border border-border bg-surface-2/60 p-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-semibold heading-serif">{template.name}</h1>
              <p className="mt-3 text-sm text-muted">{template.description}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Badge key={tag} className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="text-right text-xs text-muted">
              <div>{template.install_count || 0} installs</div>
              {template.creator?.email && <div>by {template.creator.email}</div>}
            </div>
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <Button onClick={handleInstall} disabled={installing}>
              {installing ? "Installing..." : "Install Template"}
            </Button>
            <Button variant="outline" onClick={handleShare} disabled={sharing}>
              {sharing ? "Sharing..." : "Share Template"}
            </Button>
          </div>
          {message && (
            <div className="mt-4 rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm">
              {message}
            </div>
          )}
          <div className="mt-8">
            <h2 className="text-lg font-semibold">Example Prompt</h2>
            <div className="mt-3 rounded-2xl border border-border bg-black/40 p-4 text-sm text-muted">
              {template.base_config?.prompt || "No prompt available."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
