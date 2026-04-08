export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-slate-900 to-slate-800 px-6 py-12">
      <div className="mx-auto max-w-md">{children}</div>
    </div>
  );
}
