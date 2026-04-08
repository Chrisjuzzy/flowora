"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { getMe, growthApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function GrowthPage() {
  const { data: referrals = [], refetch } = useQuery({
    queryKey: ["referrals"],
    queryFn: growthApi.referrals,
  });
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: getMe });
  const referralLink = me?.referral_code
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/ref/${me.referral_code}`
    : null;

  const claimMutation = useMutation({
    mutationFn: (id: number) => growthApi.claim(id),
    onSuccess: () => refetch(),
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[1.3fr_1fr]">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Referral Pipeline</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {referrals.map((referral: any) => (
            <div
              key={referral.id}
              className="flex items-center justify-between rounded-lg border border-border/60 bg-surface-2/60 p-4"
            >
              <div>
                <p className="font-semibold">Referral #{referral.id}</p>
                <p className="text-xs text-muted">Status: {referral.status}</p>
              </div>
              <Button
                size="sm"
                onClick={() => claimMutation.mutate(referral.id)}
                disabled={referral.reward_claimed}
              >
                {referral.reward_claimed ? "Claimed" : "Claim Reward"}
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Growth Toolkit</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted">
          <p>Share your referral link, track conversions, and reward your partners.</p>
          {referralLink ? (
            <>
              <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-xs">
                {referralLink}
              </div>
              <Button
                className="w-full"
                onClick={() => navigator.clipboard.writeText(referralLink)}
              >
                Copy Referral Link
              </Button>
            </>
          ) : (
            <Button className="w-full">Generate Referral Link</Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
