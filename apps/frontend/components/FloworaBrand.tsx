"use client";

import { useState } from "react";
import Image from "next/image";

type FloworaIconProps = {
  size?: number;
  className?: string;
  label?: string;
};

export function FloworaIcon({ size = 32, className = "", label = "Flowora" }: FloworaIconProps) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div
        className={`flex items-center justify-center rounded-2xl border border-border bg-surface-2/70 text-xs font-semibold uppercase ${className}`}
        style={{ width: size, height: size }}
        aria-label={label}
      >
        F
      </div>
    );
  }
  return (
    <Image
      src="/flowora-icon.png"
      alt={label}
      width={size}
      height={size}
      onError={() => setFailed(true)}
      className={className}
    />
  );
}

type FloworaLogoProps = {
  width?: number;
  height?: number;
  className?: string;
  label?: string;
};

export function FloworaLogo({
  width = 240,
  height = 120,
  className = "",
  label = "Flowora",
}: FloworaLogoProps) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div
        className={`flex items-center justify-center rounded-2xl border border-border bg-surface-2/70 text-base font-semibold uppercase ${className}`}
        style={{ width, height }}
        aria-label={label}
      >
        Flowora
      </div>
    );
  }
  return (
    <Image
      src="/logo.png"
      alt={label}
      width={width}
      height={height}
      onError={() => setFailed(true)}
      className={className}
    />
  );
}
