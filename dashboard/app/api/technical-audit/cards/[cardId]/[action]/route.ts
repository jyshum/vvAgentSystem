import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isConfiguredAdmin } from "@/lib/auth/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

/** Only these transitions are operator-driven. `stale` is set by the backend
 *  guard and is never requested from the UI. */
const ALLOWED_ACTIONS = new Set(["approve", "reject", "mark-applied", "verify"]);

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ cardId: string; action: string }> },
) {
  const { cardId, action } = await params;
  if (!ALLOWED_ACTIONS.has(action)) {
    return NextResponse.json({ error: "Unknown action" }, { status: 400 });
  }

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

  try {
    const res = await fetch(
      `${LANGGRAPH_API}/api/technical-audit/cards/${cardId}/${action}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${LANGGRAPH_KEY}`,
          "Content-Type": "application/json",
        },
        body: action === "approve"
          ? JSON.stringify({ approved_by: user.email })
          : undefined,
      },
    );

    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      // 409 is the stale-precondition guard refusing. Pass it through intact:
      // it is the state machine working, and the operator must see the reason.
      const status = res.status === 409 || res.status === 404 ? res.status : 502;
      return NextResponse.json(
        { error: body.detail || "Card action failed" },
        { status },
      );
    }
    return NextResponse.json({ ok: true, card: body.card });
  } catch {
    return NextResponse.json({ error: "Audit API unreachable" }, { status: 502 });
  }
}
