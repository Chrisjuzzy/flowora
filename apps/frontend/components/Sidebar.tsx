import Link from "next/link";
import { FloworaIcon } from "@/components/FloworaBrand";
import {
  Bot,
  LayoutGrid,
  Workflow,
  ShoppingBag,
  Library,
  PlayCircle,
  Users,
  Wallet,
  CreditCard,
  Megaphone,
  Shield,
  FlaskConical,
  ShieldCheck,
  Settings,
  Crown,
  Trophy,
  BarChart3,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { href: "/agents", label: "Agent Studio", icon: Bot },
  { href: "/workflows", label: "Workflow Builder", icon: Workflow },
  { href: "/marketplace", label: "Marketplace", icon: ShoppingBag },
  { href: "/templates", label: "Templates", icon: Library },
  { href: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { href: "/runs", label: "Agent Runs", icon: PlayCircle },
  { href: "/workspaces", label: "Workspaces", icon: Users },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/growth", label: "Growth & Referrals", icon: Megaphone },
  { href: "/growth-analytics", label: "Growth Analytics", icon: BarChart3 },
  { href: "/founder-mode", label: "Founder Mode", icon: Crown },
  { href: "/compliance", label: "Compliance", icon: ShieldCheck },
  { href: "/innovation", label: "Innovation Lab", icon: FlaskConical },
  { href: "/admin", label: "Admin Panel", icon: Shield },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-72 flex-shrink-0 border-r border-border bg-surface/90 px-6 py-8">
      <div className="mb-10">
        <Link href="/dashboard" className="flex items-center gap-3">
          <FloworaIcon size={28} className="h-6 w-6 md:h-7 md:w-7" />
          <span className="hidden text-sm font-semibold uppercase tracking-[0.3em] text-muted md:inline">
            Flowora
          </span>
        </Link>
        <h1 className="mt-3 text-2xl font-semibold heading-serif">Orchestrator Console</h1>
        <p className="mt-2 text-xs text-muted">Where AI Agents Flow Together</p>
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-white"
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-8 rounded-xl border border-border bg-surface-2/60 p-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-muted">
          <Settings size={14} />
          System
        </div>
        <p className="mt-2 text-sm text-muted">
          Connected to FastAPI backend. Monitor queue health and execution latency in Admin Panel.
        </p>
      </div>
    </aside>
  );
}
