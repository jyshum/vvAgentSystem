import { weekRangeLabel } from "@/lib/utils";

interface ReportHeaderProps {
  clientName: string;
  weekStart: string;
  domain?: string;
  preparedBy?: string;
}

export function ReportHeader({
  clientName,
  weekStart,
  domain,
  preparedBy = "Victory Velocity",
}: ReportHeaderProps) {
  return (
    <header className="mb-[18px]">
      <div className="flex items-center justify-between gap-4 mb-12">
        <div
          className="font-serif text-xs tracking-[0.1em] ml-auto"
          style={{ color: "var(--mute)" }}
        >
          Victory Velocity
        </div>
      </div>

      <div
        className="font-mono text-xs tracking-[0.16em] uppercase mb-3"
        style={{ color: "var(--mute)" }}
      >
        GEO &middot; Weekly Performance Report
      </div>

      <h1
        className="font-display font-light text-[72px] leading-[0.96] tracking-[-0.015em] mb-4 break-words"
        style={{ color: "var(--white)" }}
      >
        {clientName}
      </h1>

      <div
        className="font-serif italic font-light text-[21px]"
        style={{ color: "var(--mute)" }}
      >
        {weekRangeLabel(weekStart)}
      </div>

      <div
        className="font-mono text-[10px] tracking-[0.1em] uppercase mt-3"
        style={{ color: "var(--faint)" }}
      >
        {domain && `${domain} · `}Prepared by {preparedBy}
      </div>
    </header>
  );
}
