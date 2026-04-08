"use client";

import { FloworaIcon } from "@/components/FloworaBrand";

type FloworaLoaderProps = {
  show?: boolean;
  message?: string;
  fullscreen?: boolean;
};

export default function FloworaLoader({
  show = false,
  message = "Flowora is running your agents...",
  fullscreen = true,
}: FloworaLoaderProps) {
  if (!show) return null;

  const wrapperClass = fullscreen
    ? "fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
    : "flex items-center justify-center rounded-xl border border-border bg-surface-2/60 p-6";

  return (
    <div className={wrapperClass}>
      <div className="w-full max-w-lg text-center">
        <div className="relative h-24 overflow-hidden rounded-full border border-border/60 bg-surface-2/70">
          <div className="flowora-trail" />
          <div className="flowora-runner">
            <FloworaIcon
              size={72}
              className="h-12 w-12 drop-shadow-[0_8px_24px_rgba(0,0,0,0.6)]"
              label="Flowora runner"
            />
          </div>
        </div>
        <p className="mt-4 text-sm uppercase tracking-[0.2em] text-muted">Flowora</p>
        <p className="mt-2 text-lg font-semibold">{message}</p>
      </div>
    </div>
  );
}
