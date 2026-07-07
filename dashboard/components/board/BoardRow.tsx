import Link from "next/link";
import { SparklineChart } from "@/components/charts/SparklineChart";
import { formatRate, formatDelta } from "@/lib/utils";
import type { CompetitorPick, RankResult, QueryMove, OpsBadgeResult } from "@/lib/derive";

export interface BoardRowData {
  clientId: string;
  name: string;
  rate: number | null;
  delta: number | null;
  competitor: CompetitorPick | null;
  rank: RankResult | null;
  movers: QueryMove[];
  sparkline: (number | null)[];
  badge: OpsBadgeResult;
  pendingCount: number;
  firstRunPending: boolean;
}

const BADGE_COLOR: Record<string, string> = {
  error: "var(--neg)",
  waiting: "#d4a017",
  measuring: "var(--mute)",
  healthy: "var(--faint)",
};

interface BoardRowProps {
  row: BoardRowData;
  nextRunLabel?: string;
}

export function BoardRow({ row, nextRunLabel }: BoardRowProps) {
  const { name, rate, delta, competitor, rank, movers, sparkline, badge, firstRunPending, clientId } = row;

  const previousRate = rate != null && delta != null ? rate - delta : null;
  const deltaInfo = rate != null ? formatDelta(rate, previousRate) : null;
  const sparkDirection = delta == null ? "none" : delta > 0.005 ? "up" : delta < -0.005 ? "down" : "flat";

  const overviewHref = `/admin/clients/${clientId}/overview`;

  const badgeChip = (
    <span
      className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-0.5 inline-block"
      style={{ color: BADGE_COLOR[badge.kind], border: "1px solid currentColor" }}
    >
      {badge.label}
    </span>
  );

  return (
    <div
      className="grid items-center py-5 px-4 border-b"
      style={{
        gridTemplateColumns: "1.2fr 1.6fr 1.4fr 1fr",
        gap: "16px",
        borderColor: "var(--hair)",
      }}
    >
      {/* Col 1: client + delta */}
      <div>
        <Link href={overviewHref} className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
          {name}
        </Link>
        {deltaInfo && (
          <div
            className="font-mono text-[9px] mt-1"
            style={{
              color:
                deltaInfo.direction === "up"
                  ? "var(--pos)"
                  : deltaInfo.direction === "down"
                    ? "var(--neg)"
                    : "var(--mute)",
            }}
          >
            {deltaInfo.text}
          </div>
        )}
      </div>

      {/* Col 2: head-to-head hero */}
      <Link href={overviewHref} className="block">
        {firstRunPending ? (
          <div className="font-serif italic text-[13px]" style={{ color: "var(--mute)" }}>
            first run {nextRunLabel ?? "scheduled"}
          </div>
        ) : rate == null ? (
          <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
        ) : (
          <>
            <div className="flex items-baseline gap-3">
              <span className="font-display text-[34px] font-light leading-none" style={{ color: "var(--white)" }}>
                {formatRate(rate)}
              </span>
              {competitor && (
                <>
                  <span className="font-mono text-[10px] tracking-[0.1em]" style={{ color: "var(--faint)" }}>
                    VS
                  </span>
                  <span className="font-mono text-[10px] tracking-[0.06em]" style={{ color: "var(--mute)" }}>
                    {formatRate(competitor.rate)} {competitor.name.toUpperCase()}
                  </span>
                </>
              )}
            </div>
            {competitor && (
              <div className="mt-2 space-y-1">
                <div className="relative w-full" style={{ height: 3, background: "var(--ghost)" }}>
                  <div
                    className="absolute left-0 top-0 h-full"
                    style={{ width: `${Math.min(rate * 100, 100)}%`, background: "var(--white)" }}
                  />
                </div>
                <div className="relative w-full" style={{ height: 3, background: "var(--ghost)" }}>
                  <div
                    className="absolute left-0 top-0 h-full"
                    style={{ width: `${Math.min(competitor.rate * 100, 100)}%`, background: "var(--faint)" }}
                  />
                </div>
              </div>
            )}
            {rank && (
              <div className="font-mono text-[8px] mt-2" style={{ color: "var(--faint)" }}>
                #{rank.rank} OF {rank.total}
                {rank.gapToLeader === 0 ? " · LEADING" : ` · ${formatRate(rank.gapToLeader)} TO LEADER`}
              </div>
            )}
          </>
        )}
      </Link>

      {/* Col 3: biggest moves */}
      <Link href={overviewHref} className="block">
        {firstRunPending ? null : movers.length === 0 ? (
          <div className="font-serif italic text-[12px]" style={{ color: "var(--faint)" }}>
            no movement yet
          </div>
        ) : (
          <div className="space-y-1">
            {movers.map((m) => (
              <div key={m.query} className="flex items-baseline gap-1.5 min-w-0">
                <span className="font-serif text-[12px] truncate" style={{ color: "var(--mute)" }}>
                  &ldquo;{m.query}&rdquo;
                </span>
                <span
                  className="font-mono text-[10px] whitespace-nowrap shrink-0"
                  style={{ color: m.change > 0 ? "var(--pos)" : "var(--neg)" }}
                >
                  {formatRate(m.before)}→{formatRate(m.after)}
                </span>
              </div>
            ))}
          </div>
        )}
      </Link>

      {/* Col 4: sparkline + badge */}
      <div>
        {!firstRunPending && (
          <SparklineChart values={sparkline} direction={sparkDirection} width={160} height={30} />
        )}
        <div className="mt-2">
          {badge.kind === "waiting" ? <Link href="/admin/approvals">{badgeChip}</Link> : badgeChip}
        </div>
      </div>
    </div>
  );
}
