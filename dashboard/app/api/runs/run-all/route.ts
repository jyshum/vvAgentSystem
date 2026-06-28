import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST() {
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

  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "Agent API not configured" }, { status: 503 });
  }

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/run-all`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${LANGGRAPH_KEY}` },
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Could not reach agent server" }, { status: 502 });
  }
}
