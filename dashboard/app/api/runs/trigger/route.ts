import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isConfiguredAdmin } from "@/lib/auth/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized", detail: userError?.message ?? "no user session" }, { status: 401 });
  }

  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json({ error: "Config", detail: "SUPABASE_SERVICE_ROLE_KEY missing on server" }, { status: 503 });
  }

  const admin = createAdminClient();
  if (!isConfiguredAdmin(user.email)) {
    const { data: clientUser } = await admin
      .from("client_users")
      .select("role")
      .eq("user_id", user.id)
      .maybeSingle();

    if (clientUser?.role !== "admin") {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }
  }

  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "LangGraph API not configured" }, { status: 503 });
  }

  const { clientId, runType = "tracker_only" } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  const { data: client, error: clientError } = await admin.from("clients").select("id").eq("id", clientId).single();
  if (!client) {
    return NextResponse.json({ error: "Client not found", detail: clientError?.message }, { status: 404 });
  }

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/run`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${LANGGRAPH_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ client_id: clientId, run_type: runType }),
    });

    if (!res.ok) {
      const body = await res.json();
      throw new Error(body.detail || "LangGraph API error");
    }

    const data = await res.json();
    return NextResponse.json({ ok: true, thread_id: data.thread_id });
  } catch (err) {
    const message = err instanceof Error ? err.message : "LangGraph API error";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
