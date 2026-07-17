import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isConfiguredAdmin } from "@/lib/auth/admin";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

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

  const clientId = req.nextUrl.searchParams.get("clientId");
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  const { data: latest } = await admin
    .from("pipeline_runs")
    .select("id, status, run_type, stage, started_at, completed_at, error_message")
    .eq("client_id", clientId)
    .order("started_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return NextResponse.json({ run: latest ?? null });
}
