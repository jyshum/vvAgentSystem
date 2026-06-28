"use client";

import { useState } from "react";

export function RunAllButton() {
  const [state, setState] = useState<"idle" | "loading" | "triggered" | "error">("idle");

  async function trigger() {
    setState("loading");
    try {
      const res = await fetch("/api/runs/run-all", { method: "POST" });
      if (!res.ok) throw new Error("Failed");
      setState("triggered");
      setTimeout(() => setState("idle"), 30000);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 5000);
    }
  }

  const labels = {
    idle: "RUN ALL",
    loading: "STARTING...",
    triggered: "ALL RUNNING...",
    error: "ERROR",
  };

  const styles: Record<string, React.CSSProperties> = {
    idle: { background: "transparent", color: "var(--white)", border: "1px solid var(--ghost)" },
    loading: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", opacity: 0.6 },
    triggered: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", animation: "vv-pulse 1.2s ease-in-out infinite" },
    error: { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.2)" },
  };

  return (
    <>
      <style>{`@keyframes vv-pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}`}</style>
      <button
        onClick={trigger}
        disabled={state === "loading" || state === "triggered"}
        className="font-mono text-[10px] tracking-[0.14em] uppercase py-3 px-7 transition-all duration-200 hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)] disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-[var(--pos)] disabled:hover:border-[var(--pos)]"
        style={styles[state]}
      >
        {labels[state]}
      </button>
    </>
  );
}
