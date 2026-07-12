import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import { isAdminUser } from "@/lib/auth/admin";
import { NextResponse } from "next/server";

// Browser-side saves hit RLS (is_admin() only knows client_users roles, not
// ADMIN_EMAILS) and silently update 0 rows — config writes must go through
// this route, which authorizes via isAdminUser and writes with the admin client.
const UPDATABLE_FIELDS = [
  "name",
  "brand_name",
  "website_domain",
  "brand_variations",
  "competitors",
  "gsc_site_url",
  "cms_type",
  "cms_config",
  "cycle_frequency",
  "cycle_day",
] as const;

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const authClient = await createClient();
  const { data: { user } } = await authClient.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (!(await isAdminUser(user))) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const body = await request.json();
  const update: Record<string, unknown> = {};
  for (const field of UPDATABLE_FIELDS) {
    if (field in body) update[field] = body[field];
  }
  if (Object.keys(update).length === 0) {
    return NextResponse.json({ error: "No updatable fields provided" }, { status: 400 });
  }

  const supabase = createAdminClient();
  const { data, error } = await supabase
    .from("clients")
    .update(update)
    .eq("id", id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}
