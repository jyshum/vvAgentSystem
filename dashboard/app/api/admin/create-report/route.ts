import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const runId = searchParams.get("runId");
  const clientId = searchParams.get("clientId");

  if (!runId || !clientId) {
    return new Response("Missing params", { status: 400 });
  }

  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new Response("Unauthorized", { status: 401 });

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (clientUser?.role !== "admin") {
    return new Response("Forbidden", { status: 403 });
  }

  const { data: run } = await supabase
    .from("tracker_runs")
    .select("ran_at")
    .eq("id", runId)
    .single();

  if (!run) return new Response("Run not found", { status: 404 });

  const ranDate = new Date(run.ran_at);
  const day = ranDate.getDay();
  const monday = new Date(ranDate);
  monday.setDate(ranDate.getDate() - ((day + 6) % 7));
  const weekStart = monday.toISOString().split("T")[0];

  const { data: report, error } = await supabase
    .from("reports")
    .insert({
      client_id: clientId,
      run_id: runId,
      week_start: weekStart,
      status: "draft",
    })
    .select()
    .single();

  if (error) {
    return new Response(error.message, { status: 500 });
  }

  redirect(`/admin/reports/${report.id}`);
}
