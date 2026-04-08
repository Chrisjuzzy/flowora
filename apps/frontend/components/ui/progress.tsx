import * as React from "react";
import { cn } from "@/lib/utils";

const Progress = React.forwardRef<HTMLDivElement, { value: number; className?: string }>(
  ({ value, className }, ref) => (
    <div ref={ref} className={cn("h-2 w-full rounded-full bg-surface-2/60", className)}>
      <div
        className="h-2 rounded-full bg-accent transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
);
Progress.displayName = "Progress";

export { Progress };
