"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function TriggerRunButton({ clientId, latestRunAt }: { clientId: string; latestRunAt?: string | null }) {
  const [state, setState] = useState<"idle" | "loading" | "triggered" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const router = useRouter();

  // After trigger, poll every 15s for a new run row
  const poll = useCallback(async (triggeredAt: number) => {
    const supabase = createClient();
    const elapsed = Date.now() - triggeredAt;
    if (elapsed > 15 * 60 * 1000) {
      // Give up after 15 min
      setState("idle");
      return;
    }
    const { data } = await supabase
      .from("tracker_runs")
      .select("id, ran_at")
      .eq("client_id", clientId)
      .order("ran_at", { ascending: false })
      .limit(1)
      .single();

    const newRunAt = data?.ran_at;
    if (newRunAt && newRunAt !== latestRunAt) {
      // New run appeared
      router.refresh();
      setState("idle");
    } else {
      setTimeout(() => poll(triggeredAt), 15000);
    }
  }, [clientId, latestRunAt, router]);

  async function trigger() {
    setState("loading");
    setErrorMsg(null);
    try {
      const res = await fetch("/api/runs/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId, runType: "full" }),
      });
      if (!res.ok) {
        let msg = "API error";
        try {
          const body = await res.json();
          msg = body.detail ? `${body.error}: ${body.detail}` : (body.error ?? msg);
        } catch {
          msg = (await res.text()) || msg;
        }
        throw new Error(msg);
      }
      setState("triggered");
      // Start polling for the new run
      setTimeout(() => poll(Date.now()), 15000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      setState("error");
      setTimeout(() => setState("idle"), 8000);
    }
  }

  const labels = {
    idle: "RUN NOW",
    loading: "STARTING...",
    triggered: "RUNNING...",
    error: "ERROR — RETRY",
  };

  const styles: Record<string, React.CSSProperties> = {
    idle: { background: "transparent", color: "var(--white)", border: "1px solid var(--ghost)" },
    loading: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", opacity: 0.6 },
    triggered: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", animation: "vv-pulse 1.2s ease-in-out infinite" },
    error: { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.2)" },
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <style>{`@keyframes vv-pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}`}</style>
      <button
        onClick={trigger}
        disabled={state === "loading" || state === "triggered"}
        className="font-mono text-[10px] tracking-[0.14em] uppercase py-3 px-7 transition-all duration-200 hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)] flex-shrink-0 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-[var(--pos)] disabled:hover:border-[var(--pos)]"
        style={styles[state]}
      >
        {labels[state]}
      </button>
      {state === "triggered" && (
        <div className="font-mono text-[8px] tracking-[0.04em] text-right" style={{ color: "var(--mute)" }}>
          Agent running · checking every 15s
        </div>
      )}
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
