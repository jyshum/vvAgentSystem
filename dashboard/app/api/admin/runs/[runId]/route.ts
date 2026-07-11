import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { isAdminUser } from "@/lib/auth/admin";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> }
) {
  const { runId } = await params;

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return new Response("Unauthorized", { status: 401 });

  if (!(await isAdminUser(user))) {
    return new Response("Forbidden", { status: 403 });
  }

  const adminClient = createAdminClient();

  // Delete results first, then the run
  await adminClient.from("tracker_results").delete().eq("run_id", runId);
  const { error } = await adminClient.from("tracker_runs").delete().eq("id", runId);

  if (error) {
    return new Response(error.message, { status: 500 });
  }

  return new Response(null, { status: 204 });
}
