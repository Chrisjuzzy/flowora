import { Suspense } from "react";
import TemplatesClient from "./TemplatesClient";

export const dynamic = "force-dynamic";

export default function TemplatesPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted">Loading templates...</div>}>
      <TemplatesClient />
    </Suspense>
  );
}
