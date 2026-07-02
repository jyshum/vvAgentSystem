import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

function generateSlug(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 60) + "_v1"
  );
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
  const { prompt_text, bucket, set_type } = body;

  if (!prompt_text || typeof prompt_text !== "string" || !prompt_text.trim()) {
    return Response.json({ error: "prompt_text is required" }, { status: 400 });
  }

  const slug = generateSlug(prompt_text);

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("queries")
    .insert({
      client_id: clientId,
      prompt_text: prompt_text.trim(),
      slug,
      bucket: bucket || "consideration",
      set_type: set_type || "core",
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
