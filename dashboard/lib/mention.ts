export interface MentionSentence { sentence: string; brand: string }

export function extractMentionSentence(
  responseText: string,
  brandVariations: string[]
): MentionSentence | null {
  if (!responseText || brandVariations.length === 0) return null;
  const sentences = responseText
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  for (const sentence of sentences) {
    const lower = sentence.toLowerCase();
    for (const brand of brandVariations) {
      if (brand && lower.includes(brand.toLowerCase())) {
        return { sentence, brand };
      }
    }
  }
  return null;
}

export function pickRepresentative<T extends { brand_mentioned: boolean; queried_at: string }>(
  rows: T[]
): T | null {
  if (rows.length === 0) return null;
  const byRecency = [...rows].sort(
    (a, b) => new Date(b.queried_at).getTime() - new Date(a.queried_at).getTime()
  );
  return byRecency.find((r) => r.brand_mentioned) ?? byRecency[0];
}
