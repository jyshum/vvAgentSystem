"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function TriggerAuditButton({ clientId, latestAuditAt }: { clientId: string; latestAuditAt?: string | null }) {
  const [state, setState] = useState<"idle" | "loading" | "triggered" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const router = useRouter();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function startPolling(triggeredAt: number) {
    async function poll() {
      const supabase = createClient();
      const elapsed = Date.now() - triggeredAt;
      if (elapsed > 15 * 60 * 1000) {
        setState("idle");
        timerRef.current = null;
        return;
      }
      const { data } = await supabase
        .from("audit_runs")
        .select("id, ran_at")
        .eq("client_id", clientId)
        .order("ran_at", { ascending: false })
        .limit(1)
        .single();

      const newRunAt = data?.ran_at;
      if (newRunAt && newRunAt !== latestAuditAt) {
        router.refresh();
        setState("idle");
        timerRef.current = null;
      } else {
        timerRef.current = setTimeout(poll, 15000);
      }
    }

    timerRef.current = setTimeout(poll, 15000);
  }

  async function trigger() {
    setState("loading");
    setErrorMsg(null);
    try {
      const res = await fetch("/api/runs/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId, runType: "audit_only" }),
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
      startPolling(Date.now());
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      setState("error");
      setTimeout(() => setState("idle"), 8000);
    }
  }

  const labels = {
    idle: "RUN AUDIT",
    loading: "STARTING...",
    triggered: "AUDITING...",
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
          Auditing site · checking every 15s
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
