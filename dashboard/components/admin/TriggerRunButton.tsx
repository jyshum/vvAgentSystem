"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

type RunStatus = "idle" | "loading" | "running" | "awaiting_approval" | "implementing" | "completed" | "error";

const ACTIVE_STATUSES = ["running", "awaiting_approval", "implementing"];
const POLL_INTERVAL = 10_000;
const STALE_THRESHOLD = 30 * 60_000;

export function TriggerRunButton({ clientId }: { clientId: string }) {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<string | null>(null);
  const router = useRouter();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const elapsedRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimers = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (elapsedRef.current) { clearInterval(elapsedRef.current); elapsedRef.current = null; }
  }, []);

  const formatElapsed = useCallback((start: string) => {
    const sec = Math.floor((Date.now() - new Date(start).getTime()) / 1000);
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m ${sec % 60}s`;
    return `${Math.floor(min / 60)}h ${min % 60}m`;
  }, []);

  const startElapsedTimer = useCallback((start: string) => {
    setStartedAt(start);
    setElapsed(formatElapsed(start));
    if (elapsedRef.current) clearInterval(elapsedRef.current);
    elapsedRef.current = setInterval(() => setElapsed(formatElapsed(start)), 1000);
  }, [formatElapsed]);

  const checkStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/runs/status?clientId=${clientId}`);
      if (!res.ok) return;
      const { run } = await res.json();

      if (!run) {
        setStatus("idle");
        clearTimers();
        return;
      }

      if (ACTIVE_STATUSES.includes(run.status)) {
        const age = Date.now() - new Date(run.started_at).getTime();
        if (age > STALE_THRESHOLD) {
          setStatus("error");
          setErrorMsg(`Run appears stale (started ${formatElapsed(run.started_at)} ago)`);
          clearTimers();
          return;
        }
        setStatus(run.status as RunStatus);
        startElapsedTimer(run.started_at);
      } else if (run.status === "completed") {
        setStatus("completed");
        clearTimers();
        router.refresh();
        setTimeout(() => setStatus("idle"), 6000);
      } else if (run.status === "error") {
        setStatus("error");
        setErrorMsg(run.error_message || "Pipeline failed");
        clearTimers();
        setTimeout(() => setStatus("idle"), 10000);
      } else {
        setStatus("idle");
        clearTimers();
      }
    } catch {
      // Network error during poll — keep current state
    }
  }, [clientId, clearTimers, formatElapsed, startElapsedTimer, router]);

  const startPolling = useCallback(() => {
    clearTimers();
    checkStatus();
    timerRef.current = setInterval(checkStatus, POLL_INTERVAL);
  }, [checkStatus, clearTimers]);

  useEffect(() => {
    checkStatus().then(() => {
      // Only start polling if we found an active run
    });

    return clearTimers;
  }, [clientId, checkStatus, clearTimers]);

  useEffect(() => {
    if (ACTIVE_STATUSES.includes(status) && !timerRef.current) {
      timerRef.current = setInterval(checkStatus, POLL_INTERVAL);
    }
  }, [status, checkStatus]);

  async function trigger() {
    setStatus("loading");
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
      setStatus("running");
      startPolling();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      setStatus("error");
      setTimeout(() => setStatus("idle"), 8000);
    }
  }

  const isActive = status === "loading" || ACTIVE_STATUSES.includes(status);

  const labels: Record<RunStatus, string> = {
    idle: "RUN NOW",
    loading: "STARTING...",
    running: "RUNNING",
    awaiting_approval: "AWAITING APPROVAL",
    implementing: "IMPLEMENTING",
    completed: "COMPLETED ✓",
    error: "ERROR",
  };

  const colors: Record<RunStatus, string> = {
    idle: "var(--white)",
    loading: "var(--pos)",
    running: "var(--pos)",
    awaiting_approval: "#d4a017",
    implementing: "var(--pos)",
    completed: "var(--pos)",
    error: "var(--neg)",
  };

  const color = colors[status];

  const buttonStyle: React.CSSProperties = {
    background: status === "completed" ? "rgba(108,195,161,0.08)" : status === "error" ? "rgba(232,154,160,0.08)" : "transparent",
    color,
    border: `1px solid ${color}`,
    ...(isActive ? { animation: "vv-pulse 1.2s ease-in-out infinite" } : {}),
    ...(isActive ? { opacity: 0.9 } : {}),
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <style>{`@keyframes vv-pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}`}</style>
      <button
        onClick={trigger}
        disabled={isActive}
        className="font-mono text-[10px] tracking-[0.14em] uppercase py-3 px-7 cursor-pointer transition-all duration-200 active:scale-[0.97] hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)] flex-shrink-0 disabled:cursor-not-allowed disabled:active:scale-100 disabled:hover:bg-transparent disabled:hover:text-current disabled:hover:border-current"
        style={buttonStyle}
      >
        {labels[status]}
      </button>
      {isActive && (
        <div className="font-mono text-[8px] tracking-[0.04em] text-right" style={{ color: "var(--mute)" }}>
          {elapsed ? `${elapsed} elapsed` : "starting..."} · checking every 10s
        </div>
      )}
      {status === "completed" && (
        <div className="font-mono text-[8px] tracking-[0.04em] text-right" style={{ color: "var(--pos)" }}>
          Run finished successfully
        </div>
      )}
      {status === "error" && errorMsg && (
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
