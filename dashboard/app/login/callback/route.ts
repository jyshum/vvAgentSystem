import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

// Handles OAuth/magic-link callbacks (not used for password auth, kept for safety)
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}/admin`);
    }
  }

  return NextResponse.redirect(`${origin}/login`);
}
