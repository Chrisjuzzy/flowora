"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketplaceApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function LeaderboardPage() {
  const { data: listings = [], isLoading, isError, error } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: marketplaceApi.listings,
  });

  const { mostInstalled, trending, topCreators } = useMemo(() => {
    const byInstalls = [...listings].sort((a: any, b: any) => (b.downloads || 0) - (a.downloads || 0));
    const byTrend = [...listings].sort((a: any, b: any) => {
      const scoreA = (a.rating || 0) * 10 + (a.downloads || 0);
      const scoreB = (b.rating || 0) * 10 + (b.downloads || 0);
      return scoreB - scoreA;
    });

    const creatorMap = new Map<number, { seller_id: number; installs: number; listings: number }>();
    listings.forEach((listing: any) => {
      const sellerId = listing.seller_id || 0;
      const current = creatorMap.get(sellerId) || { seller_id: sellerId, installs: 0, listings: 0 };
      current.installs += listing.downloads || 0;
      current.listings += 1;
      creatorMap.set(sellerId, current);
    });
    const creators = Array.from(creatorMap.values()).sort((a, b) => b.installs - a.installs);

    return {
      mostInstalled: byInstalls.slice(0, 5),
      trending: byTrend.slice(0, 5),
      topCreators: creators.slice(0, 5),
    };
  }, [listings]);

  if (isLoading)
    return (
      <div className="grid gap-4 p-8 md:grid-cols-3">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    );
  if (isError) return <div className="p-8 text-red-400">{(error as Error)?.message}</div>;
  if (!listings.length) return <div className="p-8 text-muted">No leaderboard data yet.</div>;

  return (
    <div className="space-y-6">
      <Card className="app-surface">
        <CardHeader>
          <CardTitle className="heading-serif">Community Leaderboard</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-3">
          <div className="space-y-3">
            <p className="text-sm text-muted">Most Installed Agents</p>
            {mostInstalled.map((listing: any) => (
              <div key={listing.id} className="rounded-lg border border-border/60 bg-surface-2/60 p-3">
                <p className="font-semibold">{listing.agent?.name || "Agent Listing"}</p>
                <p className="text-xs text-muted">{listing.downloads || 0} installs</p>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            <p className="text-sm text-muted">Trending Agents</p>
            {trending.map((listing: any) => (
              <div key={listing.id} className="rounded-lg border border-border/60 bg-surface-2/60 p-3">
                <p className="font-semibold">{listing.agent?.name || "Agent Listing"}</p>
                <p className="text-xs text-muted">
                  {(listing.rating || 0).toFixed(1)} rating • {listing.downloads || 0} installs
                </p>
              </div>
            ))}
          </div>

          <div className="space-y-3">
            <p className="text-sm text-muted">Top Creators</p>
            {topCreators.map((creator) => (
              <div key={creator.seller_id} className="rounded-lg border border-border/60 bg-surface-2/60 p-3">
                <p className="font-semibold">Creator #{creator.seller_id || "system"}</p>
                <p className="text-xs text-muted">
                  {creator.installs} installs • {creator.listings} listings
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
