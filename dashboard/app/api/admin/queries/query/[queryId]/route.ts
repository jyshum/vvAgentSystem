import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

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

const BUCKETS = new Set(["awareness", "consideration", "branded"]);
const SET_TYPES = new Set(["core", "discovery"]);
const STATUSES = new Set(["active", "retired"]);

function validParaphrases(p: unknown): string[] {
  if (p === undefined || p === null) return [];
  if (!Array.isArray(p) || p.some((x) => typeof x !== "string" || !x.trim())) {
    throw new Error("paraphrases must be an array of non-empty strings");
  }
  return (p as string[]).map((x) => x.trim());
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const body = await request.json();
  const updates: Record<string, unknown> = {};

  if (body.bucket !== undefined) {
    if (!BUCKETS.has(body.bucket)) return Response.json({ error: "Invalid bucket" }, { status: 400 });
    updates.bucket = body.bucket;
  }
  if (body.set_type !== undefined) {
    if (!SET_TYPES.has(body.set_type)) return Response.json({ error: "Invalid set_type" }, { status: 400 });
    updates.set_type = body.set_type;
  }
  if (body.status !== undefined) {
    if (!STATUSES.has(body.status)) return Response.json({ error: "Invalid status" }, { status: 400 });
    updates.status = body.status;
    if (body.status === "retired") {
      updates.retired_at = new Date().toISOString();
    }
  }
  if (body.paraphrases !== undefined) {
    try {
      updates.paraphrases = validParaphrases(body.paraphrases);
    } catch (e) {
      return Response.json({ error: (e as Error).message }, { status: 400 });
    }
  }

  if (Object.keys(updates).length === 0) {
    return Response.json({ error: "No valid fields to update" }, { status: 400 });
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .update(updates)
    .eq("id", queryId)
    .select()
    .single();

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return Response.json(data);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ queryId: string }> }
) {
  const { queryId } = await params;
  const supabase = await createClient();
  const user = await checkAdmin(supabase);
  if (!user) return Response.json({ error: "Forbidden" }, { status: 403 });

  const admin = createAdminClient();
  const { error } = await admin.from("queries").delete().eq("id", queryId);

  if (error) return Response.json({ error: error.message }, { status: 500 });
  return new Response(null, { status: 204 });
}
