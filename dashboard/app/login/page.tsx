"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({ email, password });

    setLoading(false);
    if (authError) {
      setError("Invalid email or password.");
    } else {
      router.push("/admin");
      router.refresh();
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-6"
      style={{ background: "var(--ink)" }}
    >
      <div className="w-full max-w-[360px]">
        {/* Brand */}
        <div className="text-center mb-14">
          <h1 className="font-display text-[26px] font-light" style={{ color: "var(--white)" }}>
            Victory<em style={{ fontStyle: "italic", color: "var(--mute)" }}>Velocity</em>
          </h1>
          <p
            className="font-mono text-[9px] tracking-[0.22em] uppercase mt-2"
            style={{ color: "var(--faint)" }}
          >
            Admin
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              className="block font-mono text-[9px] tracking-[0.14em] uppercase mb-1.5"
              style={{ color: "var(--faint)" }}
            >
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
              className="w-full bg-transparent font-mono text-[12px] px-3 py-2.5 outline-none transition-colors"
              style={{ border: "1px solid var(--ghost)", color: "var(--white)" }}
              onFocus={(e) => (e.target.style.borderColor = "rgba(245,244,241,0.42)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--ghost)")}
            />
          </div>

          <div>
            <label
              className="block font-mono text-[9px] tracking-[0.14em] uppercase mb-1.5"
              style={{ color: "var(--faint)" }}
            >
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
              className="w-full bg-transparent font-mono text-[12px] px-3 py-2.5 outline-none transition-colors"
              style={{ border: "1px solid var(--ghost)", color: "var(--white)" }}
              onFocus={(e) => (e.target.style.borderColor = "rgba(245,244,241,0.42)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--ghost)")}
            />
          </div>

          {error && (
            <p className="font-mono text-[9px] tracking-[0.08em]" style={{ color: "var(--neg)" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 font-mono text-[10px] tracking-[0.14em] uppercase py-3.5 transition-all duration-200 hover:opacity-90"
            style={{
              background: "var(--white)",
              color: "var(--ink)",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
