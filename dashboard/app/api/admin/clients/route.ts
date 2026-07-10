import { normalizeIntent, type IntentImportItem } from "@/lib/intent-import";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextResponse } from "next/server";
import type { Query } from "@/lib/types";

function generateSlug(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 60) + "_v1"
  );
}

export async function POST(request: Request) {
  const supabase = createAdminClient();

  const body = await request.json();
  const { name, brand_name, website_domain, brand_variations, target_queries, query_buckets, intents, competitors } = body;

  if (!name?.trim() || !website_domain?.trim()) {
    return NextResponse.json({ error: "name and website_domain are required" }, { status: 400 });
  }

  let intentRows: IntentImportItem[];
  try {
    intentRows = buildIntentRows(intents);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Intent JSON is invalid." },
      { status: 400 }
    );
  }

  const legacyPrompts = Array.isArray(target_queries)
    ? target_queries.map((q) => String(q).trim()).filter(Boolean)
    : [];
  const bucketPrompts = buildBucketPrompts(query_buckets);
  const prompts = intentRows.length > 0
    ? intentRows
    : bucketPrompts.length > 0
      ? bucketPrompts
      : legacyPrompts.map((prompt_text) => ({
          prompt_text,
          bucket: "consideration" as const,
          paraphrases: [],
        }));

  const { data, error } = await supabase
    .from("clients")
    .insert({
      name: name.trim(),
      brand_name: (brand_name?.trim() || name.trim()),
      website_domain: website_domain.trim(),
      brand_variations: brand_variations ?? [],
      target_queries: target_queries ?? [],
      competitors: competitors ?? [],
    })
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  if (prompts.length > 0) {
    const { error: queryError } = await supabase.from("queries").insert(
      prompts.map(({ prompt_text, bucket, paraphrases }) => ({
        client_id: data.id,
        prompt_text,
        slug: generateSlug(prompt_text),
        bucket,
        set_type: "core",
        paraphrases,
      }))
    );
    if (queryError) {
      return NextResponse.json({ error: queryError.message }, { status: 500 });
    }
  }

  return NextResponse.json(data, { status: 201 });
}

function buildIntentRows(input: unknown): IntentImportItem[] {
  if (input === undefined || input === null) return [];
  if (!Array.isArray(input)) throw new Error("intents must be an array");
  return input.map(normalizeIntent);
}

function buildBucketPrompts(input: unknown): IntentImportItem[] {
  if (!input || typeof input !== "object") return [];
  const buckets = input as Record<string, unknown>;
  return (["awareness", "consideration", "branded"] as Query["bucket"][]).flatMap((bucket) => {
    const values = buckets[bucket];
    if (!Array.isArray(values)) return [];
    return values
      .map((value) => String(value).trim())
      .filter(Boolean)
      .map((prompt_text) => ({ prompt_text, bucket, paraphrases: [] }));
  });
}
