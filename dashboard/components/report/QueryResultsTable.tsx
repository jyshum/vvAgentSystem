import { Badge } from "@/components/ui/Badge";
import type { TrackerResultClient } from "@/lib/types";

interface QueryResultsTableProps {
  results: TrackerResultClient[];
}

export function QueryResultsTable({ results }: QueryResultsTableProps) {
  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
        style={{ color: "var(--mute)" }}
      >
        GEO Query Results
      </h2>

      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)", width: "42%" }}
            >
              Query
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)", width: "16%" }}
            >
              Engine
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)", width: "14%" }}
            >
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={r.id}>
              <td
                className="font-serif italic text-lg py-[13px] pr-3.5 border-b border-[var(--hair)] align-top leading-snug"
                style={{ color: "var(--white)" }}
              >
                {r.query}
              </td>
              <td
                className="font-mono text-[10px] tracking-[0.08em] uppercase py-[13px] pr-3.5 border-b border-[var(--hair)] align-top"
                style={{ color: "var(--faint)" }}
              >
                {r.engine}
              </td>
              <td className="py-[13px] border-b border-[var(--hair)] align-top">
                {r.brand_cited ? (
                  <Badge variant="cited">Cited</Badge>
                ) : r.brand_mentioned ? (
                  <Badge variant="mentioned">Mentioned</Badge>
                ) : (
                  <Badge variant="not-found">Not Found</Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
