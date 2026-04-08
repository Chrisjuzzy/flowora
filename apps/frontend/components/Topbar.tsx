import { Search, Bell, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Topbar() {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-border/60 px-8 py-6">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-muted">Workspace Overview</p>
        <h2 className="mt-2 text-2xl font-semibold heading-serif">Flowora Command Center</h2>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-full border border-border bg-surface-2/70 px-3 py-2 text-sm text-muted">
          <Search size={16} />
          <span>Search agents, runs, workflows...</span>
        </div>
        <Button variant="secondary" size="icon">
          <Bell size={16} />
        </Button>
        <Button>
          <Sparkles size={16} />
          New Deployment
        </Button>
      </div>
    </header>
  );
}
