import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (clientUser?.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const { email, clientId } = await request.json();
  if (!email || !clientId) {
    return NextResponse.json(
      { error: "Missing email or clientId" },
      { status: 400 }
    );
  }

  const admin = createAdminClient();

  const { data: inviteData, error: inviteError } =
    await admin.auth.admin.inviteUserByEmail(email, {
      redirectTo: `${request.headers.get("origin")}/login/callback`,
    });

  if (inviteError) {
    return NextResponse.json(
      { error: inviteError.message },
      { status: 500 }
    );
  }

  if (inviteData.user) {
    await admin.from("client_users").insert({
      user_id: inviteData.user.id,
      client_id: clientId,
      role: "client",
    });
  }

  return NextResponse.json({ success: true });
}
