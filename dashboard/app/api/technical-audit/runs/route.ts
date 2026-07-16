import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isConfiguredAdmin } from "@/lib/auth/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (!process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json(
      { error: "SUPABASE_SERVICE_ROLE_KEY missing on server" },
      { status: 503 },
    );
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
    return NextResponse.json({ error: "Audit API not configured" }, { status: 503 });
  }

  const { clientId } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/technical-audit/runs`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LANGGRAPH_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ client_id: clientId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return NextResponse.json(
        { error: body.detail || "Audit API error" },
        { status: res.status === 404 ? 404 : 502 },
      );
    }
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ error: "Audit API unreachable" }, { status: 502 });
  }
}
