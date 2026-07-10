import { describe, expect, it } from "vitest";
import {
  BUCKET_DETAILS,
  BUCKET_LABELS,
  contentAuthorityScore,
  productVisibilityScore,
} from "@/lib/intent-labels";
import type { TrackerRun } from "@/lib/types";

function runWithBuckets(bucket_scores: TrackerRun["bucket_scores"]): TrackerRun {
  return {
    id: "run-1",
    client_id: "client-1",
    ran_at: "2026-07-10T00:00:00Z",
    aggregate_mention_rate: 0.91,
    non_branded_mention_rate: 0.91,
    aggregate_avg_mention_level: 2,
    bucket_scores,
    per_engine_scores: {},
    competitor_scores: {},
    gsc_clicks: 0,
    gsc_impressions: 0,
    gsc_ctr: 0,
    gsc_position: 0,
    gsc_top_queries: [],
    discovered_competitors: [],
    query_set_signature: null,
    query_set_changed: false,
  };
}

describe("intent labels", () => {
  it("maps internal buckets to product labels", () => {
    expect(BUCKET_LABELS.consideration).toBe("Product Visibility");
    expect(BUCKET_LABELS.awareness).toBe("Content Authority");
    expect(BUCKET_LABELS.branded).toBe("Branded - Deferred");
    expect(BUCKET_DETAILS.consideration).toContain("Product");
    expect(BUCKET_DETAILS.awareness).toContain("Content");
  });

  it("uses consideration for product visibility and does not fall back to the merged score", () => {
    const run = runWithBuckets({
      consideration: { mention_rate: 0.42, avg_mention_level: 2.1, citation_rate: 0.2, intent_count: 6 },
      awareness: { mention_rate: 0.76, avg_mention_level: 2.8, citation_rate: 0.5, intent_count: 3 },
    });

    expect(productVisibilityScore(run)).toEqual({
      mention_rate: 0.42,
      avg_mention_level: 2.1,
      citation_rate: 0.2,
      intent_count: 6,
    });
  });

  it("returns null product visibility when no consideration bucket exists", () => {
    const run = runWithBuckets({
      awareness: { mention_rate: 0.76, avg_mention_level: 2.8, citation_rate: 0.5, intent_count: 3 },
    });

    expect(productVisibilityScore(run)).toBeNull();
  });

  it("uses awareness for content authority", () => {
    const run = runWithBuckets({
      awareness: { mention_rate: 0.31, avg_mention_level: 1.8, citation_rate: 0.44, intent_count: 4 },
    });

    expect(contentAuthorityScore(run)).toEqual({
      mention_rate: 0.31,
      avg_mention_level: 1.8,
      citation_rate: 0.44,
      intent_count: 4,
    });
  });
});
