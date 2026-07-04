import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role, client_id")
    .eq("user_id", user.id)
    .single();

  if (!clientUser || clientUser.role !== "client") redirect("/admin");

  const { data: client } = await supabase
    .from("clients")
    .select("name")
    .eq("id", clientUser.client_id)
    .single();

  return (
    <div className="min-h-screen" style={{ background: "var(--ink)" }}>
      <nav
        className="no-print h-[78px] flex items-center justify-between px-14"
        style={{
          background: "rgba(14,14,15,0.82)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--hair)",
        }}
      >
        <span
          className="font-serif text-[21px] tracking-[0.01em]"
          style={{ color: "var(--white)" }}
        >
          Victory Velocity
        </span>

        <div className="flex items-center gap-[30px]">
          <Link
            href="/dashboard"
            className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors hover:text-[var(--white)]"
            style={{ color: "var(--mute)" }}
          >
            Dashboard
          </Link>
          <span
            className="font-mono text-[10px] tracking-[0.1em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            {client?.name}
          </span>
          <form action="/api/auth/signout" method="POST">
            <button
              type="submit"
              className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors bg-transparent border-none cursor-pointer hover:text-[var(--white)]"
              style={{ color: "var(--faint)" }}
            >
              Sign Out
            </button>
          </form>
        </div>
      </nav>

      <main className="max-w-[1280px] mx-auto px-14 py-12">
        {children}
      </main>
    </div>
  );
}
