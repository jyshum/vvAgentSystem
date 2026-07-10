import type { Query } from "@/lib/types";

const BUCKETS = new Set<Query["bucket"]>(["awareness", "consideration", "branded"]);

export interface IntentImportItem {
  prompt_text: string;
  bucket: Query["bucket"];
  paraphrases: string[];
}

export interface IntentImportRow extends IntentImportItem {
  client_id: string;
  slug: string;
  set_type: "core";
}

function generateSlugBase(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 60)
  );
}

export function normalizeIntent(input: unknown): IntentImportItem {
  if (!input || typeof input !== "object") {
    throw new Error("each intent must be an object");
  }

  const row = input as Record<string, unknown>;
  if (typeof row.prompt_text !== "string" || !row.prompt_text.trim()) {
    throw new Error("each intent needs prompt_text");
  }

  const bucket = row.bucket === undefined ? "consideration" : row.bucket;
  if (typeof bucket !== "string" || !BUCKETS.has(bucket as Query["bucket"])) {
    throw new Error(`invalid bucket: ${String(bucket)}`);
  }

  const paraphrases = row.paraphrases ?? [];
  if (
    !Array.isArray(paraphrases) ||
    paraphrases.some((value) => typeof value !== "string" || !value.trim())
  ) {
    throw new Error("paraphrases must be an array of non-empty strings");
  }

  return {
    prompt_text: row.prompt_text.trim(),
    bucket: bucket as Query["bucket"],
    paraphrases: paraphrases.map((value) => value.trim()),
  };
}

export function parseIntentJson(text: string): IntentImportItem[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("Intent JSON is invalid.");
  }

  if (!Array.isArray(parsed)) {
    throw new Error("Expected a JSON array of intents.");
  }
  if (parsed.length === 0) {
    throw new Error("Import must include at least one intent.");
  }

  return parsed.map(normalizeIntent);
}

function nextSlug(promptText: string, usedSlugs: Set<string>): string {
  const base = generateSlugBase(promptText) || "intent";
  let version = 1;
  let slug = `${base}_v${version}`;
  while (usedSlugs.has(slug)) {
    version += 1;
    slug = `${base}_v${version}`;
  }
  usedSlugs.add(slug);
  return slug;
}

export function buildIntentImportRows(
  clientId: string,
  intents: unknown[],
  existingSlugs: Set<string> = new Set()
): IntentImportRow[] {
  if (intents.length === 0) {
    throw new Error("Import must include at least one intent.");
  }

  const usedSlugs = new Set(existingSlugs);
  return intents.map((intent) => {
    const normalized = normalizeIntent(intent);
    return {
      client_id: clientId,
      prompt_text: normalized.prompt_text,
      slug: nextSlug(normalized.prompt_text, usedSlugs),
      bucket: normalized.bucket,
      set_type: "core",
      paraphrases: normalized.paraphrases,
    };
  });
}
