"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  CARD_ALLOWED_TRANSITIONS,
  type TechnicalAuditCardStatus,
} from "@/lib/technical-audit-types";

/** Maps a target status to the backend action route segment and its label.
 *  Only transitions an operator drives are listed; `stale` and
 *  `still_failing` are set by the backend guard, never requested from the
 *  UI. */
const ACTIONS: Partial<
  Record<TechnicalAuditCardStatus, { action: string; label: string; primary?: boolean }>
> = {
  approved: { action: "approve", label: "Approve", primary: true },
  rejected: { action: "reject", label: "Reject" },
  applied: { action: "mark-applied", label: "Mark applied", primary: true },
  verified: { action: "verify", label: "Verify", primary: true },
};

const BUTTON =
  "border px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.1em] disabled:opacity-40";

export function CardActions({
  cardId,
  status,
}: {
  cardId: string;
  status: TechnicalAuditCardStatus;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const targets = (CARD_ALLOWED_TRANSITIONS[status] ?? []).filter(
    (target) => ACTIONS[target],
  );

  async function run(action: string) {
    setPending(true);
    setError(null);
    try {
      const res = await fetch(`/api/technical-audit/cards/${cardId}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || `Request failed (${res.status})`);
        return;
      }
      router.refresh();
    } catch {
      setError("Network error");
    } finally {
      setPending(false);
    }
  }

  if (targets.length === 0 && !error) return null;

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {targets.map((target) => {
          const config = ACTIONS[target]!;
          return (
            <button
              key={target}
              type="button"
              disabled={pending}
              onClick={() => run(config.action)}
              className={BUTTON}
              style={{
                color: config.primary ? "var(--pos)" : "var(--white)",
                borderColor: config.primary ? "var(--pos)" : "var(--faint)",
              }}
            >
              {config.label}
            </button>
          );
        })}
      </div>
      {error && (
        <p
          role="alert"
          className="mt-2 font-serif text-[12px]"
          style={{ color: "var(--neg)" }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
