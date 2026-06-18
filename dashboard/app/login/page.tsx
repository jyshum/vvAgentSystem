"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/login/callback`,
      },
    });

    setLoading(false);
    if (authError) {
      setError("Something went wrong. Please try again.");
    } else {
      setSent(true);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6"
         style={{ background: "var(--ink)" }}>
      <div className="w-full max-w-[400px]">
        {/* Brand */}
        <div className="text-center mb-16">
          <h1 className="font-serif text-[21px] tracking-[0.01em]"
              style={{ color: "var(--white)" }}>
            Victory Velocity
          </h1>
          <p className="font-mono text-[10px] tracking-[0.2em] uppercase mt-2"
             style={{ color: "var(--faint)" }}>
            Client Dashboard
          </p>
        </div>

        {sent ? (
          <div className="text-center">
            <p className="font-serif text-lg italic"
               style={{ color: "var(--mute)" }}>
              Check your email for a login link.
            </p>
            <p className="font-mono text-[10px] tracking-[0.1em] uppercase mt-4"
               style={{ color: "var(--faint)" }}>
              Sent to {email}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <label className="block font-mono text-[11px] tracking-[0.12em] uppercase mb-2"
                   style={{ color: "var(--mute)" }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              className="w-full bg-transparent font-serif text-sm px-3 py-2.5 outline-none transition-colors"
              style={{
                border: "1px solid var(--ghost)",
                color: "var(--white)",
              }}
              onFocus={(e) =>
                (e.target.style.borderColor = "rgba(245,244,241,0.42)")
              }
              onBlur={(e) =>
                (e.target.style.borderColor = "var(--ghost)")
              }
            />

            {error && (
              <p className="font-mono text-[10px] tracking-[0.1em] mt-2"
                 style={{ color: "var(--neg)" }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-6 font-sans text-[13px] font-semibold tracking-[0.06em] inline-flex items-center justify-center py-[15px] px-[26px] cursor-pointer transition-all duration-300"
              style={{
                background: "var(--white)",
                color: "var(--ink)",
                border: "1px solid var(--white)",
                borderRadius: "2px",
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? "Sending…" : "Send Magic Link"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
