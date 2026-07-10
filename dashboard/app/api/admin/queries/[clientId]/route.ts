import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { buildIntentImportRows } from "@/lib/intent-import";

function generateSlug(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 60) + "_v1"
  );
}

const BUCKETS = new Set(["awareness", "consideration", "branded"]);
const SET_TYPES = new Set(["core", "discovery"]);

function validParaphrases(p: unknown): string[] {
  if (p === undefined || p === null) return [];
  if (!Array.isArray(p) || p.some((x) => typeof x !== "string" || !x.trim())) {
    throw new Error("paraphrases must be an array of non-empty strings");
  }
  return (p as string[]).map((x) => x.trim());
}

async function checkAdmin(supabase: Awaited<ReturnType<typeof createClient>>) {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  return clientUser?.role === "admin" ? user : null;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .select("*")
    .eq("client_id", clientId)
    .order("created_at", { ascending: true });

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json(data);
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const body = await request.json();

  if (Array.isArray(body?.intents)) {
    let rows;
    try {
      rows = buildIntentImportRows(clientId, body.intents);
    } catch (e) {
      return Response.json({ error: (e as Error).message }, { status: 400 });
    }

    const admin = createAdminClient();
    const mode = body?.mode === "replace_active" ? "replace_active" : "append";
    if (mode === "replace_active") {
      const retiredAt = new Date().toISOString();
      const { error: retireError } = await admin
        .from("queries")
        .update({ status: "retired", retired_at: retiredAt })
        .eq("client_id", clientId)
        .eq("status", "active");

      if (retireError) return Response.json({ error: retireError.message }, { status: 500 });
    }

    const { data, error } = await admin.from("queries").insert(rows).select();
    if (error) return Response.json({ error: error.message }, { status: 500 });
    return Response.json(data, { status: 201 });
  }

  const { prompt_text, bucket, set_type } = body;

  if (!prompt_text || typeof prompt_text !== "string" || !prompt_text.trim()) {
    return Response.json({ error: "prompt_text is required" }, { status: 400 });
  }
  if (bucket !== undefined && !BUCKETS.has(bucket)) {
    return Response.json({ error: "Invalid bucket" }, { status: 400 });
  }
  if (set_type !== undefined && !SET_TYPES.has(set_type)) {
    return Response.json({ error: "Invalid set_type" }, { status: 400 });
  }

  const slug = generateSlug(prompt_text);
  let paraphrases: string[];
  try {
    paraphrases = validParaphrases(body.paraphrases);
  } catch (e) {
    return Response.json({ error: (e as Error).message }, { status: 400 });
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .insert({
      client_id: clientId,
      prompt_text: prompt_text.trim(),
      slug,
      bucket: bucket || "consideration",
      set_type: set_type || "core",
      paraphrases,
    })
    .select()
    .single();

  if (error) {
    if (error.code === "23505") {
      return Response.json({ error: "A query with this slug already exists" }, { status: 409 });
    }
    return Response.json({ error: error.message }, { status: 500 });
  }

  return Response.json(data, { status: 201 });
}
