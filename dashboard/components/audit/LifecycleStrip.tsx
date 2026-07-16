import {
  LIFECYCLE_COLOR,
  LIFECYCLE_LABEL,
  LIFECYCLE_STRIP_ORDER,
  type TechnicalAuditLifecycleState,
} from "@/lib/technical-audit-types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function LifecycleStrip({
  counts,
  previousRunAt,
}: {
  counts: Partial<Record<TechnicalAuditLifecycleState, number>>;
  previousRunAt: string | null;
}) {
  if (!previousRunAt) return null;

  const items = LIFECYCLE_STRIP_ORDER.filter((state) => (counts[state] ?? 0) > 0);
  if (items.length === 0) return null;

  return (
    <div
      className="mb-6 flex flex-wrap items-center gap-x-7 gap-y-2 border px-4 py-3"
      style={{ borderColor: "var(--hair)" }}
    >
      <span
        className="font-mono text-[8px] uppercase tracking-[0.12em]"
        style={{ color: "var(--faint)" }}
      >
        Since {formatDate(previousRunAt)}
      </span>
      {items.map((state) => (
        <span
          key={state}
          data-testid="lifecycle-item"
          className="font-serif text-[13px]"
          style={{ color: LIFECYCLE_COLOR[state] }}
        >
          {counts[state]} {LIFECYCLE_LABEL[state]}
        </span>
      ))}
    </div>
  );
}
