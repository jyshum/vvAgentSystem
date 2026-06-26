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
        <div className="font-display text-[22px]" style={{ color: "var(--white)" }}>
          Victory<em style={{ fontStyle: "italic", color: "var(--mute)" }}>Velocity</em>
        </div>

        <Link
          href="/admin/approvals"
          className="font-mono text-[10px] tracking-[0.12em] uppercase transition-colors hover:text-[var(--white)]"
          style={{ color: "var(--faint)" }}
        >
          APPROVALS
        </Link>

        <form action="/api/auth/signout" method="POST">
          <button
            type="submit"
            className="font-mono text-[10px] tracking-[0.12em] uppercase bg-transparent border-none cursor-pointer transition-colors hover:text-[var(--white)]"
            style={{ color: "var(--faint)" }}
          >
            SIGN OUT
          </button>
        </form>
      </nav>

      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "56px 56px 100px" }}>
        {children}
      </main>
    </div>
  );
}
