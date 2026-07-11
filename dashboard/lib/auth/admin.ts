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
