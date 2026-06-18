import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function AdminLayout({
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
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (!clientUser || clientUser.role !== "admin") redirect("/dashboard");

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
        <div className="flex items-center gap-3">
          <span
            className="font-serif text-[21px] tracking-[0.01em]"
            style={{ color: "var(--white)" }}
          >
            Victory Velocity
          </span>
          <span
            className="font-mono text-[8px] tracking-[0.2em] uppercase py-[3px] px-[7px]"
            style={{
              color: "var(--mute)",
              border: "1px solid var(--ghost)",
            }}
          >
            Admin
          </span>
        </div>

        <div className="flex items-center gap-[30px]">
          <Link
            href="/admin"
            className="font-sans text-[12.5px] font-medium tracking-[0.08em] transition-colors hover:text-[var(--white)]"
            style={{ color: "var(--mute)" }}
          >
            Clients
          </Link>
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
