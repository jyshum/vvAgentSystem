"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function TriggerRunButton({ clientId }: { clientId: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const router = useRouter();

  async function trigger() {
    setState("loading");
    setErrorMsg(null);
    try {
      const res = await fetch("/api/runs/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId }),
      });
      if (!res.ok) {
        let msg = "Railway API error";
        try {
          const body = await res.json();
          msg = body.error ?? msg;
        } catch {
          msg = (await res.text()) || msg;
        }
        throw new Error(msg);
      }
      setState("done");
      setTimeout(() => {
        router.refresh();
        setState("idle");
      }, 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      setState("error");
      setTimeout(() => setState("idle"), 5000);
    }
  }

  const labels = {
    idle: "RUN NOW",
    loading: "RUNNING...",
    done: "TRIGGERED",
    error: "ERROR — RETRY",
  };

  const styles: Record<string, React.CSSProperties> = {
    idle: { background: "transparent", color: "var(--white)", border: "1px solid var(--ghost)" },
    loading: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", animation: "vv-pulse 1.2s ease-in-out infinite" },
    done: { background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.3)" },
    error: { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.2)" },
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <style>{`@keyframes vv-pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}`}</style>
      <button
        onClick={trigger}
        disabled={state === "loading"}
        className="font-mono text-[10px] tracking-[0.14em] uppercase py-3 px-7 transition-all duration-200 hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)] flex-shrink-0"
        style={styles[state]}
      >
        {labels[state]}
      </button>
      {state === "error" && errorMsg && (
        <div
          className="font-mono text-[8px] tracking-[0.04em] max-w-[280px] text-right leading-relaxed"
          style={{ color: "var(--neg)" }}
        >
          {errorMsg}
        </div>
      )}
    </div>
  );
}
