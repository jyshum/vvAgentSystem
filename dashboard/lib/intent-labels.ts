import type { Query, TrackerRun } from "@/lib/types";

export const BUCKET_LABELS: Record<Query["bucket"], string> = {
  awareness: "Content Authority",
  consideration: "Product Visibility",
  branded: "Branded - Deferred",
};

export const BUCKET_DETAILS: Record<Query["bucket"], string> = {
  awareness: "Content education and how-to intents; measured as authority and citation signal",
  consideration: "Product, tool, platform, template, and resource-selection intents",
  branded: "Deferred - not measured in current runs",
};

export type BucketScore = NonNullable<TrackerRun["bucket_scores"][Query["bucket"]]>;

export function productVisibilityScore(run: Pick<TrackerRun, "bucket_scores">): BucketScore | null {
  return run.bucket_scores?.consideration ?? null;
}

export function contentAuthorityScore(run: Pick<TrackerRun, "bucket_scores">): BucketScore | null {
  return run.bucket_scores?.awareness ?? null;
}
