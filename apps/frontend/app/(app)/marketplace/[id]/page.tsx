"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { agentsApi, getAgent, getAgentReviews, createReview, buyListing, installAgent, getMarketplaceAgents } from "@/lib/api";
import { Agent, AgentReview, MarketplaceListing } from "@/types";

export default function AgentStorePage({ params }: { params: { id: string } }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [listing, setListing] = useState<MarketplaceListing | null>(null);
  const [reviews, setReviews] = useState<AgentReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [newReview, setNewReview] = useState({ rating: 5, comment: "" });
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();
  const agentId = parseInt(params.id);

  useEffect(() => {
    loadData();
  }, [agentId]);

  const loadData = async () => {
    try {
      const agentData = await getAgent(agentId);
      setAgent(agentData);

      const listings = await getMarketplaceAgents();
      const found = listings.find((l: any) => l.agent_id === agentId);
      setListing(found || null);

      const reviewsData = await getAgentReviews(agentId);
      setReviews(reviewsData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async () => {
    if (!listing) return;
    try {
      if (listing.price > 0) {
        if (!confirm(`Buy for $${listing.price}?`)) return;
        await buyListing(listing.id);
      }
      await installAgent(agentId);
      setMessage("Installed to your workspace.");
      router.push("/dashboard");
    } catch (e: any) {
      alert("Action failed: " + e.message);
    }
  };

  const handleClone = async () => {
    try {
      await agentsApi.clone(agentId);
      setMessage("Cloned to your workspace.");
      router.push("/agents");
    } catch (e: any) {
      alert("Clone failed: " + e.message);
    }
  };

  const submitReview = async () => {
    try {
      await createReview(agentId, newReview.rating, newReview.comment);
      setNewReview({ rating: 5, comment: "" });
      loadData();
    } catch (e: any) {
      alert("Review failed: " + e.message);
    }
  };

  if (loading) return <div className="p-8">Loading...</div>;
  if (!agent) return <div className="p-8">Agent not found</div>;

  return (
    <div className="space-y-6">
      <button onClick={() => router.back()} className="text-muted hover:text-white">
        &larr; Back to Marketplace
      </button>

      <div className="app-surface rounded-xl p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">{agent.name}</h1>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted mb-4">
              <span className="bg-surface-2/60 text-white px-2 py-1 rounded-full">v{agent.version}</span>
              <span>{agent.category || "General"}</span>
              <span>By User #{agent.owner_id}</span>
            </div>
            <p className="text-muted text-lg mb-6">{agent.description}</p>
            {agent.tags && (
              <div className="flex flex-wrap gap-2">
                {agent.tags.split(",").map((tag) => (
                  <span key={tag} className="bg-surface-2/60 text-muted px-2 py-1 rounded text-xs">
                    #{tag.trim()}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="bg-surface-2/70 p-6 rounded-xl border border-border text-center min-w-[200px]">
            <div className="text-3xl font-bold mb-2">
              {listing?.price && listing.price > 0 ? `$${listing.price}` : "Free"}
            </div>
            <button
              onClick={handlePurchase}
              className="w-full bg-accent text-black py-3 rounded-lg font-bold hover:bg-amber-300 transition"
            >
              {listing?.price && listing.price > 0 ? "Buy Now" : "Install"}
            </button>
            <button
              onClick={handleClone}
              className="mt-3 w-full border border-border/60 py-3 rounded-lg font-semibold text-muted hover:text-white transition"
            >
              Clone Agent
            </button>
          </div>
        </div>
        {message && <p className="mt-4 text-sm text-muted">{message}</p>}
      </div>

      <div className="app-surface rounded-xl p-8">
        <h2 className="text-2xl font-bold mb-6">Reviews</h2>

        <div className="mb-8 p-6 bg-surface-2/60 rounded-xl">
          <h3 className="font-bold mb-4">Write a Review</h3>
          <div className="flex gap-4 mb-4">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => setNewReview({ ...newReview, rating: star })}
                className={`text-2xl ${star <= newReview.rating ? "text-yellow-400" : "text-muted"}`}
              >
                *
              </button>
            ))}
          </div>
          <textarea
            className="w-full p-3 border border-border rounded-lg mb-4 bg-surface-2/60 text-white"
            placeholder="Share your experience..."
            value={newReview.comment}
            onChange={(e) => setNewReview({ ...newReview, comment: e.target.value })}
          />
          <button onClick={submitReview} className="px-6 py-2 bg-accent text-black rounded-lg hover:bg-amber-300">
            Post Review
          </button>
        </div>

        <div className="space-y-6">
          {reviews.map((review) => (
            <div key={review.id} className="border-b border-border/60 pb-6 last:border-0">
              <div className="flex justify-between mb-2">
                <span className="font-bold">User #{review.user_id}</span>
                <span className="text-yellow-400">{"*".repeat(review.rating)}</span>
              </div>
              <p className="text-muted">{review.comment}</p>
              <span className="text-xs text-muted mt-2 block">
                {new Date(review.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
          {reviews.length === 0 && <p className="text-muted text-center py-8">No reviews yet.</p>}
        </div>
      </div>
    </div>
  );
}
