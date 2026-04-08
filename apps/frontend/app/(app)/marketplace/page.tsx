"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { agentsApi, marketplaceApi } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Star, ShoppingCart, Upload } from "lucide-react";

export default function MarketplacePage() {
  const { data: listings = [], refetch, isLoading, isError, error } = useQuery({
    queryKey: ["marketplace"],
    queryFn: marketplaceApi.listings,
  });
  const { data: agents = [] } = useQuery({ queryKey: ["agents"], queryFn: agentsApi.list });
  const [flash, setFlash] = useState<string | null>(null);
  const [publishForm, setPublishForm] = useState({
    agent_id: "",
    price: 10,
    category: "growth",
    description: "",
  });

  const buyMutation = useMutation({
    mutationFn: (listingId: number) => marketplaceApi.buy(listingId),
    onSuccess: () => setFlash("Purchase completed."),
  });

  const installMutation = useMutation({
    mutationFn: (agentId: number) => marketplaceApi.install(agentId),
    onSuccess: () => setFlash("Agent installed to your workspace."),
  });

  const publishMutation = useMutation({
    mutationFn: async () => {
      if (!publishForm.agent_id) return null;
      await agentsApi.publish(Number(publishForm.agent_id), {
        category: publishForm.category,
        description: publishForm.description,
        version: "1.0.0",
      });
      return marketplaceApi.createListing({
        agent_id: Number(publishForm.agent_id),
        price: publishForm.price,
        category: publishForm.category,
        is_active: true,
        listing_type: "agent",
      });
    },
    onSuccess: () => {
      refetch();
      setPublishForm({ agent_id: "", price: 10, category: "growth", description: "" });
      setFlash("Listing published.");
    },
  });

  const { mostInstalled, trending, topCreators } = useMemo(() => {
    const byInstalls = [...listings].sort((a: any, b: any) => (b.downloads || 0) - (a.downloads || 0));
    const byTrend = [...listings].sort((a: any, b: any) => {
      const scoreA = (a.rating || 0) * 10 + (a.downloads || 0);
      const scoreB = (b.rating || 0) * 10 + (b.downloads || 0);
      return scoreB - scoreA;
    });
    const creatorMap = new Map<number, { seller_id: number; installs: number }>();
    listings.forEach((listing: any) => {
      const sellerId = listing.seller_id || 0;
      const current = creatorMap.get(sellerId) || { seller_id: sellerId, installs: 0 };
      current.installs += listing.downloads || 0;
      creatorMap.set(sellerId, current);
    });
    const creators = Array.from(creatorMap.values()).sort((a, b) => b.installs - a.installs);
    return {
      mostInstalled: byInstalls.slice(0, 4),
      trending: byTrend.slice(0, 4),
      topCreators: creators.slice(0, 4),
    };
  }, [listings]);

  return (
    <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
      <div className="space-y-6">
        {flash && <div className="rounded-lg border border-border/60 bg-surface-2/60 p-3 text-sm">{flash}</div>}
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Marketplace Highlights</CardTitle>
            <CardDescription>Trending agents, top installs, and leading creators.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted">Trending</p>
              <div className="mt-3 space-y-2 text-sm">
                {trending.map((listing: any) => (
                  <div key={listing.id} className="flex items-center justify-between">
                    <span>{listing.agent?.name || "Agent"}</span>
                    <span className="text-xs text-muted">{listing.rating?.toFixed(1) || "4.8"}</span>
                  </div>
                ))}
                {!trending.length && <p className="text-xs text-muted">No data yet.</p>}
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted">Most Installed</p>
              <div className="mt-3 space-y-2 text-sm">
                {mostInstalled.map((listing: any) => (
                  <div key={listing.id} className="flex items-center justify-between">
                    <span>{listing.agent?.name || "Agent"}</span>
                    <span className="text-xs text-muted">{listing.downloads || 0}</span>
                  </div>
                ))}
                {!mostInstalled.length && <p className="text-xs text-muted">No data yet.</p>}
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-muted">Top Creators</p>
              <div className="mt-3 space-y-2 text-sm">
                {topCreators.map((creator) => (
                  <div key={creator.seller_id} className="flex items-center justify-between">
                    <span>Creator #{creator.seller_id || "system"}</span>
                    <span className="text-xs text-muted">{creator.installs} installs</span>
                  </div>
                ))}
                {!topCreators.length && <p className="text-xs text-muted">No data yet.</p>}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="app-surface">
          <CardHeader>
            <CardTitle className="heading-serif">Flowora Marketplace</CardTitle>
            <CardDescription>Discover, buy, and install production-ready agents.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {isLoading && (
              <>
                <Skeleton className="h-36" />
                <Skeleton className="h-36" />
              </>
            )}
            {isError && (
              <div className="col-span-full text-sm text-red-400">{(error as Error)?.message}</div>
            )}
            {!isLoading && listings.length === 0 && (
              <div className="col-span-full text-sm text-muted">No listings yet. Publish one to get started.</div>
            )}
            {listings.map((listing: any) => (
              <div key={listing.id} className="rounded-xl border border-border/60 bg-surface-2/60 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-lg font-semibold">{listing.agent?.name || "Agent Listing"}</p>
                    <p className="text-xs text-muted">{listing.category || "general"}</p>
                  </div>
                  <Badge variant="accent">${listing.price}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted">
                  {listing.agent?.description || "Marketplace agent template."}
                </p>
                <div className="mt-3 flex items-center gap-2 text-xs text-muted">
                  <Star size={14} /> {listing.rating?.toFixed(1) || "4.8"} rating
                  <span>•</span>
                  <span>Creator #{listing.seller_id || "system"}</span>
                  <span>•</span>
                  <span>{listing.downloads || 0} installs</span>
                  <span>•</span>
                  <span>{listing.reviews?.length || 0} reviews</span>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => buyMutation.mutate(listing.id)}
                    disabled={buyMutation.isPending}
                  >
                    <ShoppingCart size={14} /> Buy
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => installMutation.mutate(listing.agent_id)}
                  >
                    Install
                  </Button>
                  <Link
                    href={`/a/${listing.agent_id}`}
                    className="self-center text-xs text-muted hover:text-white"
                  >
                    Share
                  </Link>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="app-surface h-fit">
        <CardHeader>
          <CardTitle className="heading-serif">Publish Agent</CardTitle>
          <CardDescription>List your agents with pricing, assets, and categories.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select
            value={publishForm.agent_id}
            onChange={(e) => setPublishForm((prev) => ({ ...prev, agent_id: e.target.value }))}
          >
            <option value="">Select an agent</option>
            {agents.map((agent: any) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </Select>
          <Input
            type="number"
            min="1"
            value={publishForm.price}
            onChange={(e) => setPublishForm((prev) => ({ ...prev, price: Number(e.target.value) }))}
            placeholder="Price"
          />
          <Input
            value={publishForm.category}
            onChange={(e) => setPublishForm((prev) => ({ ...prev, category: e.target.value }))}
            placeholder="Category"
          />
          <Textarea
            value={publishForm.description}
            onChange={(e) => setPublishForm((prev) => ({ ...prev, description: e.target.value }))}
            placeholder="Describe your agent"
          />
          <div className="rounded-lg border border-dashed border-border/80 bg-surface-2/40 p-4 text-sm text-muted">
            <Upload size={16} /> Upload screenshots (drag & drop)
          </div>
          <Button className="w-full" onClick={() => publishMutation.mutate()}>
            Publish Listing
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
