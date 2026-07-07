import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const admin = createAdminClient();
  const { data: clientUser } = await admin
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (!clientUser || clientUser.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const { threadId, approvedCardIds, rejectedCardIds } = await req.json();
  const approved: string[] = approvedCardIds || [];
  const rejected: string[] = rejectedCardIds || [];

  for (const cardId of approved) {
    await admin.from("action_cards").update({ status: "approved" }).eq("id", cardId);
  }
  for (const cardId of rejected) {
    await admin.from("action_cards").update({ status: "rejected" }).eq("id", cardId);
  }

  if (LANGGRAPH_API && LANGGRAPH_KEY && threadId) {
    try {
      const res = await fetch(`${LANGGRAPH_API}/api/approve`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${LANGGRAPH_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ thread_id: threadId, approved_card_ids: approved, rejected_card_ids: rejected }),
      });
      if (!res.ok) {
        const body = await res.json();
        return NextResponse.json({ error: body.detail || "LangGraph resume failed" }, { status: 502 });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "LangGraph API error";
      return NextResponse.json({ error: msg }, { status: 502 });
    }
  }

  return NextResponse.json({ ok: true });
}
