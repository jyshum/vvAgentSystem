import { createAdminClient } from "@/lib/supabase/admin";
import type { ActionCard } from "@/lib/improvement-types";

type CardRow = Pick<
  ActionCard,
  "id" | "action_type" | "page_url" | "status" | "auto_approved" | "verification" | "preview_url" | "created_at" | "query_id" | "cms_action"
>;

const STATUS_ORDER: { key: CardRow["status"]; label: string }[] = [
  { key: "pending", label: "PENDING" },
  { key: "approved", label: "APPROVED" },
  { key: "implemented", label: "IMPLEMENTED" },
  { key: "rejected", label: "REJECTED" },
];

function pathnameOf(url: string | null): string {
  if (!url) return "—";
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

export default async function CardsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data } = await supabase
    .from("action_cards")
    .select("id, action_type, page_url, status, auto_approved, verification, preview_url, created_at, query_id, cms_action")
    .eq("client_id", id)
    .order("created_at", { ascending: false });

  const cards = (data as CardRow[]) || [];

  if (cards.length === 0) {
    return (
      <p className="font-serif italic" style={{ color: "var(--mute)" }}>
        No cards yet.
      </p>
    );
  }

  const sections = STATUS_ORDER.map(({ key, label }) => ({
    label,
    cards: cards.filter((c) => c.status === key),
  })).filter((s) => s.cards.length > 0);

  return (
    <div>
      {sections.map((section) => (
        <div key={section.label} className="mb-8">
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-3" style={{ color: "var(--faint)" }}>
            {section.label} <span style={{ color: "var(--mute)" }}>({section.cards.length})</span>
          </div>
          {section.cards.map((card) => (
            <div
              key={card.id}
              className="flex items-center gap-4 py-3 border-b"
              style={{ borderColor: "var(--hair)" }}
            >
              <div className="font-mono text-[9px] flex-shrink-0" style={{ color: "var(--faint)", width: 90 }}>
                {new Date(card.created_at).toLocaleDateString()}
              </div>
              <div className="font-mono text-[9px] flex-shrink-0" style={{ color: "var(--white)", width: 140 }}>
                {card.action_type}
              </div>
              <div className="font-mono text-[9px] flex-1 truncate" style={{ color: "var(--mute)" }}>
                {pathnameOf(card.page_url)}
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {card.auto_approved && (
                  <span
                    className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                    style={{ color: "var(--mute)", border: "1px solid var(--mute)" }}
                  >
                    AUTO
                  </span>
                )}
                {card.verification != null && (
                  <span
                    className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                    style={{
                      color: card.verification.verified === true ? "var(--pos)" : "#d4a017",
                      border: `1px solid ${card.verification.verified === true ? "var(--pos)" : "#d4a017"}`,
                    }}
                  >
                    {card.verification.verified === true ? "VERIFIED ✓" : "NOT VERIFIED"}
                  </span>
                )}
                {card.preview_url && (
                  <a
                    href={card.preview_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-mono text-[8px] tracking-[0.08em] uppercase px-1.5 py-0.5"
                    style={{ color: "var(--white)", border: "1px solid var(--ghost)" }}
                  >
                    PR/PREVIEW →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
