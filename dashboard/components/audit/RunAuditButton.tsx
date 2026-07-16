"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function RunAuditButton({ clientId }: { clientId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setPending(true);
    setError(null);
    try {
      const res = await fetch("/api/technical-audit/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || `Could not start audit (${res.status})`);
        return;
      }
      router.refresh();
    } catch {
      setError("Network error");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={run}
        disabled={pending}
        className="border px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] disabled:opacity-40"
        style={{ color: "var(--pos)", borderColor: "var(--pos)" }}
      >
        {pending ? "Starting" : "Run audit"}
      </button>
      {error && (
        <span role="alert" className="font-serif text-[11px]" style={{ color: "var(--neg)" }}>
          {error}
        </span>
      )}
    </div>
  );
}
