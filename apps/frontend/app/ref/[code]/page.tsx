"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ReferralPage({ params }: { params: { code: string } }) {
  const router = useRouter();

  useEffect(() => {
    if (!params.code) return;
    localStorage.setItem("flowora_referral_code", params.code);
    router.replace(`/register?ref=${params.code}`);
  }, [params.code, router]);

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="text-center">
        <p className="text-sm text-muted">Applying your referral link...</p>
      </div>
    </div>
  );
}
