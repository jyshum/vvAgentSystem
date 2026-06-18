"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function TriggerRunButton({ clientId }: { clientId: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const router = useRouter();

  async function trigger() {
    setState("loading");
    try {
      const res = await fetch("/api/runs/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId }),
      });
      if (!res.ok) throw new Error(await res.text());
      setState("done");
      setTimeout(() => {
        setState("idle");
        router.refresh();
      }, 3000);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }

  const labels = {
    idle: "RUN TRACKER →",
    loading: "TRIGGERING…",
    done: "TRIGGERED ✓",
    error: "ERROR — RETRY",
  };

  const styles = {
    idle: { background: "transparent", color: "var(--white)", border: "1px solid var(--ghost)" },
    loading: { background: "transparent", color: "var(--faint)", border: "1px solid var(--hair)", opacity: 0.7 },
    done: { background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)" },
    error: { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.2)" },
  };

  return (
    <button
      onClick={trigger}
      disabled={state === "loading"}
      className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-all duration-200"
      style={styles[state]}
    >
      {labels[state]}
    </button>
  );
}
