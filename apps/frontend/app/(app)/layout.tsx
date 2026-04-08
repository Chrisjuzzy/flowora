import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import AuthGuard from "@/components/AuthGuard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 bg-gradient-to-br from-slate-950/70 via-slate-900/60 to-slate-950/80">
          <Topbar />
          <main className="px-8 py-8">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
