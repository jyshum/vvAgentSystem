import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { productVisibilityScore } from "@/lib/intent-labels";
import { scoreColor, formatRate } from "@/lib/utils";
import type { Client, TrackerRun, Report } from "@/lib/types";

interface ClientCardProps {
  client: Client;
  latestRun: TrackerRun | null;
  latestReport: Report | null;
}

export function ClientCard({
  client,
  latestRun,
  latestReport,
}: ClientCardProps) {
  const rate = latestRun ? productVisibilityScore(latestRun)?.mention_rate ?? null : null;

  return (
    <Card elevated className="p-6">
      <h3
        className="font-serif text-[28px] font-normal tracking-[-0.02em] mb-1"
        style={{ color: "var(--white)" }}
      >
        {client.name}
      </h3>

      <div
        className="font-mono text-[11px] tracking-[0.1em] uppercase mb-4"
        style={{ color: "var(--faint)" }}
      >
        {client.website_domain || "no domain"}
      </div>

      {rate != null && (
        <div className="mb-2">
          <span
            className="font-serif text-[40px] font-light leading-none"
            style={{ color: scoreColor(rate) }}
          >
            {formatRate(rate)}
          </span>
          <span
            className="font-mono text-[9px] tracking-[0.1em] uppercase ml-2"
            style={{ color: "var(--faint)" }}
          >
            product visibility
          </span>
        </div>
      )}

      <div
        className="font-mono text-[10px] tracking-[0.08em] mb-4"
        style={{ color: "var(--faint)" }}
      >
        {latestRun
          ? `Last run: ${new Date(latestRun.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
          : "No runs yet"}
      </div>

      <div className="flex items-center gap-2 mb-4">
        {latestReport ? (
          <Badge variant={latestReport.status === "published" ? "published" : "draft"}>
            {latestReport.status}
          </Badge>
        ) : (
          <span
            className="font-mono text-[8px] tracking-[0.1em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            No report
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <Link
          href={`/admin/clients/${client.id}`}
          className="font-sans text-[13px] font-semibold tracking-[0.06em] inline-flex items-center py-[11px] px-[20px] transition-all duration-300 border rounded-[2px]"
          style={{
            borderColor: "var(--ghost)",
            color: "var(--white)",
          }}
        >
          View
        </Link>
      </div>
    </Card>
  );
}
