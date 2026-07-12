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

export interface CompetitorCount { name: string; count: number }

/** Union of competitor names across all sampled responses, with occurrence counts. */
export function aggregateCompetitorMentions(
  rows: { competitor_mentions: string[] | null }[]
): CompetitorCount[] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    for (const name of row.competitor_mentions ?? []) {
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

export interface MentionEvidence { wording: string; sentence: string; brand: string }

/** One evidence sentence per mentioned response, tagged with the wording that produced it. */
export function extractAllMentionEvidence(
  rows: { brand_mentioned: boolean; query: string; response_text: string | null }[],
  brandVariations: string[]
): MentionEvidence[] {
  const out: MentionEvidence[] = [];
  for (const row of rows) {
    if (!row.brand_mentioned || !row.response_text) continue;
    const hit = extractMentionSentence(row.response_text, brandVariations);
    if (hit) out.push({ wording: row.query, ...hit });
  }
  return out;
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
