import { createAdminClient } from "@/lib/supabase/admin";

export function isConfiguredAdmin(
  email: string | undefined,
  configuredEmails = process.env.ADMIN_EMAILS
): boolean {
  if (!email) return false;

  const allowedEmails = (configuredEmails ?? "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);

  return allowedEmails.includes(email.toLowerCase());
}

/** True when the user is an ADMIN_EMAILS admin or has an admin role in client_users. */
export async function isAdminUser(user: { id: string; email?: string }): Promise<boolean> {
  if (isConfiguredAdmin(user.email)) return true;

  const admin = createAdminClient();
  const { data } = await admin
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .maybeSingle();

  return data?.role === "admin";
}
