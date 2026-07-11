import Link from "next/link";
import { TimelineChart } from "@/components/charts/TimelineChart";
import { SparklineChart } from "@/components/charts/SparklineChart";
import { formatRate } from "@/lib/utils";

const clients = [
  {
    id: "fake-budget-md",
    name: "BudgetYourMD",
    domain: "budgetyourmd.fake",
    rate: 0.38,
    previous: 0.31,
    competitor: { name: "MD Financial", rate: 0.62 },
    rank: "#3 OF 5",
    badge: "4 CARDS · 2D",
    badgeColor: "#d4a017",
    sparkline: [0.19, 0.24, 0.27, 0.31, 0.38],
    movers: [
      ["medical school debt calculator", 0.18, 0.42],
      ["budget template for residents", 0.39, 0.21],
    ],
  },
  {
    id: "fake-childspot",
    name: "ChildSpot",
    domain: "childspotapp.fake",
    rate: 0.47,
    previous: 0.49,
    competitor: { name: "Brightwheel", rate: 0.71 },
    rank: "#2 OF 6",
    badge: "HEALTHY",
    badgeColor: "var(--faint)",
    sparkline: [0.43, 0.45, 0.51, 0.49, 0.47],
    movers: [
      ["daycare management app", 0.55, 0.62],
      ["childcare billing software", 0.33, 0.18],
    ],
  },
  {
    id: "fake-northline",
    name: "Northline Legal",
    domain: "northlinelegal.fake",
    rate: null,
    previous: null,
    competitor: null,
    rank: "FIRST RUN SCHEDULED",
    badge: "MEASURING",
    badgeColor: "var(--mute)",
    sparkline: [],
    movers: [],
  },
];

const runs = [
  { label: "Jun 10", value: 0.19, comp: 0.58 },
  { label: "Jun 17", value: 0.24, comp: 0.6 },
  { label: "Jun 24", value: 0.27, comp: 0.65 },
  { label: "Jul 1", value: 0.31, comp: 0.61 },
  { label: "Jul 8", value: 0.38, comp: 0.62 },
];

const heatRows = [
  {
    bucket: "Awareness",
    rows: [
      ["How to budget as a medical student in Canada", [0.17, 0.25, 0.33, 0.42, 0.5], "gaining", "22%", "/blog/med-student-budget", "MD Financial 58%", "1 WAITING"],
      ["How much debt does the average Canadian medical student graduate with", [0, 0.08, 0.08, 0.17, 0.25], "gaining", "—", "/guides/debt", "RBC 42%", "—"],
      ["How to save money during medical school", [0.33, 0.25, 0.17, 0.17, 0.08], "declining", "14%", "—", "MD Financial 67%", "2 WAITING"],
    ],
  },
  {
    bucket: "Consideration",
    rows: [
      ["Best budgeting tools for medical students", [0.42, 0.5, 0.58, 0.67, 0.75], "locked_in", "44%", "/tools/budget-template", "YNAB 50%", "—"],
      ["Medical student budget template Canada", [0.17, 0.25, 0.33, 0.25, 0.42], "volatile", "20%", "/templates/canada", "MD Financial 58%", "1 WAITING"],
      ["Best newsletter for medical student personal finance", [0, 0, 0.08, 0.17, 0.25], "gaining", "—", "—", "White Coat Investor 50%", "—"],
    ],
  },
  {
    bucket: "Branded",
    rows: [
      ["Budget Your MD review", [0.75, 0.83, 0.92, 0.92, 1], "locked_in", "67%", "/playbook", "—", "—"],
      ["Budget Your MD financial playbook worth it", [0.58, 0.67, 0.67, 0.75, 0.83], "locked_in", "50%", "/financial-playbook", "—", "—"],
    ],
  },
];

const cards = [
  {
    type: "ADD FAQ SCHEMA",
    query: "medical school debt calculator",
    page: "/guides/debt",
    priority: "HIGH",
    status: "PENDING",
    reason: "AI engines cite competitor resources when asked about repayment planning.",
  },
  {
    type: "REWRITE INTRO",
    query: "budget template for residents",
    page: "/templates/canada",
    priority: "MED",
    status: "AUTO",
    reason: "Page matches the query, but the answer is buried below the fold.",
  },
  {
    type: "CREATE CONTENT",
    query: "newsletter for medical student personal finance",
    page: "content gap",
    priority: "MED",
    status: "PENDING",
    reason: "No strong page exists for newsletter/resource discovery prompts.",
  },
];

const pipeline = [
  ["TRACKER", "38%", "non-branded mention rate"],
  ["CRAWLABILITY", "CLEAR", "robots, CDN, JS render pass"],
  ["PAGES", "42", "pages inventoried"],
  ["MATCHING", "6", "6 matched · 1 weak · 2 gaps"],
  ["READINESS", "72", "avg 72 · lowest 41"],
  ["CARDS", "4", "2 auto · 2 to you"],
];

function delta(current: number | null, previous: number | null) {
  if (current == null || previous == null) return null;
  const pp = Math.round((current - previous) * 100);
  return `${pp > 0 ? "+" : ""}${pp}pp`;
}

function heatBg(rate: number) {
  if (rate === 0) return "rgba(232,154,160,0.14)";
  if (rate < 0.25) return "rgba(253,126,20,0.12)";
  if (rate < 0.5) return "rgba(255,193,7,0.10)";
  return "rgba(132,216,171,0.14)";
}

export default function CurrentFrontendMockPage() {
  return (
    <div className="min-h-screen" style={{ background: "var(--ink)", color: "var(--white)" }}>
      <nav
        className="h-[78px] flex items-center justify-between px-14"
        style={{ background: "rgba(14,14,15,0.82)", backdropFilter: "blur(12px)", borderBottom: "1px solid var(--hair)" }}
      >
        <div className="font-display text-[22px]" style={{ color: "var(--white)" }}>
          Victory<em style={{ fontStyle: "italic", color: "var(--mute)" }}>Velocity</em>
        </div>
        <div className="flex items-center gap-8">
          {["BOARD", "CLIENTS", "APPROVALS"].map((label) => (
            <span key={label} className="font-mono text-[10px] tracking-[0.12em] uppercase" style={{ color: label === "BOARD" ? "var(--white)" : "var(--faint)" }}>
              {label}
            </span>
          ))}
        </div>
        <Link href="/" className="font-mono text-[10px] tracking-[0.12em] uppercase" style={{ color: "var(--faint)" }}>
          MOCK ONLY
        </Link>
      </nav>

      <main style={{ maxWidth: 1080, margin: "0 auto", padding: "56px 56px 100px" }}>
        <section className="mb-14">
          <h1 className="font-display text-[52px] font-light leading-[0.96]" style={{ color: "var(--white)" }}>
            Board
          </h1>
          <p className="font-serif italic text-base mt-2" style={{ color: "var(--mute)" }}>
            AI visibility across the portfolio
          </p>
          <div className="mt-8 mb-8 font-mono text-[9px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
            <span style={{ color: "var(--pos)" }}>1 IMPROVING</span>
            {" · "}
            <span style={{ color: "var(--neg)" }}>1 DECLINING</span>
            {" · "}
            <span>1 FLAT</span>
            {" — "}
            <span style={{ color: "#d4a017" }}>7 CARDS TO REVIEW</span>
            {" — "}
            <span>0 ERRORS</span>
          </div>

          <div style={{ borderTop: "1px solid var(--hair)" }}>
            {clients.map((client) => {
              const change = delta(client.rate, client.previous);
              return (
                <div
                  key={client.id}
                  className="grid items-center py-5 px-4 border-b"
                  style={{ gridTemplateColumns: "1.2fr 1.6fr 1.4fr 1fr", gap: "16px", borderColor: "var(--hair)" }}
                >
                  <div>
                    <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
                      {client.name}
                    </div>
                    {change && (
                      <div className="font-mono text-[9px] mt-1" style={{ color: change.startsWith("+") ? "var(--pos)" : "var(--neg)" }}>
                        {change}
                      </div>
                    )}
                  </div>
                  <div>
                    {client.rate == null ? (
                      <div className="font-serif italic text-[13px]" style={{ color: "var(--mute)" }}>
                        first run Fri 2:00 AM
                      </div>
                    ) : (
                      <>
                        <div className="flex items-baseline gap-3">
                          <span className="font-display text-[34px] font-light leading-none">{formatRate(client.rate)}</span>
                          {client.competitor && (
                            <>
                              <span className="font-mono text-[10px] tracking-[0.1em]" style={{ color: "var(--faint)" }}>VS</span>
                              <span className="font-mono text-[10px] tracking-[0.06em]" style={{ color: "var(--mute)" }}>
                                {formatRate(client.competitor.rate)} {client.competitor.name.toUpperCase()}
                              </span>
                            </>
                          )}
                        </div>
                        <div className="font-mono text-[8px] mt-2" style={{ color: "var(--faint)" }}>{client.rank}</div>
                      </>
                    )}
                  </div>
                  <div>
                    {client.movers.length === 0 ? (
                      <div className="font-serif italic text-[12px]" style={{ color: "var(--faint)" }}>no movement yet</div>
                    ) : (
                      <div className="space-y-1">
                        {client.movers.map(([query, before, after]) => (
                          <div key={query as string} className="flex items-baseline gap-1.5 min-w-0">
                            <span className="font-serif text-[12px] truncate" style={{ color: "var(--mute)" }}>
                              &ldquo;{query}&rdquo;
                            </span>
                            <span className="font-mono text-[10px] whitespace-nowrap" style={{ color: (after as number) > (before as number) ? "var(--pos)" : "var(--neg)" }}>
                              {formatRate(before as number)}→{formatRate(after as number)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div>
                    {client.sparkline.length > 0 && <SparklineChart values={client.sparkline} direction={client.rate! > client.previous! ? "up" : "down"} width={160} height={30} />}
                    <div className="mt-2">
                      <span className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-0.5 inline-block" style={{ color: client.badgeColor, border: "1px solid currentColor" }}>
                        {client.badge}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="mb-14">
          <div className="flex items-end justify-between gap-5 mb-8 pb-3.5 border-b" style={{ borderColor: "var(--hair)" }}>
            <div>
              <div className="font-mono text-[9px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
                CLIENTS / BUDGETYOURMD
              </div>
              <h2 className="font-display text-[48px] font-light leading-[0.95] mt-6">BudgetYourMD</h2>
              <div className="font-mono text-[10px] tracking-[0.1em] mt-1.5" style={{ color: "var(--faint)" }}>
                budgetyourmd.fake
              </div>
              <div className="mt-5 flex items-baseline gap-4 flex-wrap">
                <span className="font-display text-[84px] font-light leading-none">38%</span>
                <span className="font-mono text-lg" style={{ color: "var(--pos)" }}>+7pp</span>
                <span className="font-mono text-[11px] leading-[1.6]" style={{ color: "var(--mute)" }}>
                  VS MD FINANCIAL 62%
                  <br />#3 OF 5
                </span>
              </div>
              <div className="font-serif text-[13px] mt-2.5" style={{ color: "var(--mute)" }}>
                cited as source: 31% of non-branded mentions <span style={{ color: "var(--faint)" }}>· branded coverage: 92%</span>
              </div>
            </div>
            <button className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5" style={{ background: "var(--white)", color: "var(--ink)" }}>
              RUN NOW
            </button>
          </div>

          <div className="flex gap-0 border-b mb-10" style={{ borderColor: "var(--hair)" }}>
            {["OVERVIEW", "QUERIES", "PAGES", "RUNS", "CARDS", "CONFIG", "REPORTS"].map((tab, i) => (
              <div
                key={tab}
                className="font-mono text-[9px] tracking-[0.14em] uppercase px-4 py-3 border-t border-l border-r"
                style={{ color: i === 0 ? "var(--white)" : "var(--faint)", borderColor: i === 0 ? "var(--hair)" : "transparent" }}
              >
                {tab}
              </div>
            ))}
          </div>

          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
            VISIBILITY TIMELINE
          </div>
          <TimelineChart
            series={runs.map((r) => ({ label: r.label, value: r.value }))}
            competitor={{ name: "MD FINANCIAL", series: runs.map((r) => r.comp) }}
          />
        </section>

        <section className="mb-14">
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
            QUERY × CYCLE
          </div>
          <div
            className="grid px-4 pb-3 border-b"
            style={{ gridTemplateColumns: "2fr repeat(5, 44px) 0.8fr 0.6fr 1.2fr 1fr 0.8fr", gap: 12, borderColor: "var(--hair)" }}
          >
            {["QUERY", "6/10", "6/17", "6/24", "7/1", "7/8", "STABILITY", "CITED", "PAGE", "TOP COMPETITOR", "WAITING"].map((h) => (
              <div key={h} className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
                {h}
              </div>
            ))}
          </div>
          {heatRows.map((group) => (
            <div key={group.bucket}>
              <div className="px-4 py-3 font-mono text-[9px] tracking-[0.18em] uppercase" style={{ color: group.bucket === "Branded" ? "#d4a017" : "var(--faint)", borderBottom: "1px solid var(--hair)" }}>
                {group.bucket} · {group.rows.length}
                {group.bucket === "Branded" ? " · tracked separately from primary score" : ""}
              </div>
              {group.rows.map(([query, rates, stability, cited, page, topCompetitor, waiting]) => (
                <div
                  key={query as string}
                  className="grid items-center px-4 py-3 border-b"
                  style={{ gridTemplateColumns: "2fr repeat(5, 44px) 0.8fr 0.6fr 1.2fr 1fr 0.8fr", gap: 12, borderColor: "var(--hair)" }}
                >
                  <div className="font-serif text-[14px]">{query}</div>
                  {(rates as number[]).map((rate, i) => (
                    <div key={i} className="font-mono text-[10px] text-center py-1" style={{ background: heatBg(rate), color: "var(--white)" }}>
                      {formatRate(rate)}
                    </div>
                  ))}
                  <div className="font-mono text-[9px] lowercase" style={{ color: stability === "declining" ? "var(--neg)" : stability === "volatile" ? "#d4a017" : "var(--pos)" }}>
                    {stability}
                  </div>
                  <div className="font-mono text-[10px]" style={{ color: "var(--mute)" }}>{cited}</div>
                  <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>{page}</div>
                  <div className="font-serif text-[12px]" style={{ color: "var(--mute)" }}>{topCompetitor}</div>
                  <div>
                    {waiting === "—" ? (
                      <span className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>—</span>
                    ) : (
                      <span className="font-mono text-[8px] tracking-[0.08em] px-1.5 py-0.5" style={{ color: "#d4a017", border: "1px solid #d4a017" }}>
                        {waiting}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </section>

        <section className="mb-14">
          <h2 className="font-display text-[38px] font-light leading-[0.96] mb-2">Run — July 8, 2026</h2>
          <div className="font-mono text-[10px] tracking-[0.08em] mb-6" style={{ color: "var(--mute)" }}>
            3m 18s · <span className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1" style={{ color: "var(--pos)", border: "1px solid var(--pos)" }}>completed</span>
          </div>
          <div className="grid grid-cols-3 mb-8" style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}>
            {pipeline.map(([label, value, detail]) => (
              <div key={label} className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
                <div className="font-mono text-[8px] tracking-[0.14em] mb-1.5" style={{ color: "var(--faint)" }}>{label}</div>
                <div className="font-display font-light text-[38px] leading-none" style={{ color: value === "CLEAR" ? "var(--pos)" : "var(--white)" }}>{value}</div>
                <div className="font-serif text-[12px] mt-1.5" style={{ color: "var(--mute)" }}>{detail}</div>
              </div>
            ))}
          </div>
          <div className="font-mono text-[10px] tracking-[0.06em]" style={{ color: "var(--mute)" }}>
            24 queries → 18 matched → 42 scored → 6 gaps → 4 cards → 2 auto + 2 to you
          </div>
        </section>

        <section>
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
            ACTION CARDS
          </div>
          <div className="grid grid-cols-3" style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}>
            {cards.map((card) => (
              <div key={card.query} className="p-5" style={{ background: "var(--ink)" }}>
                <div className="flex items-center justify-between gap-3 mb-4">
                  <span className="font-mono text-[8px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>{card.type}</span>
                  <span className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1" style={{ color: card.status === "PENDING" ? "#d4a017" : "var(--pos)", border: "1px solid currentColor" }}>{card.status}</span>
                </div>
                <div className="font-serif text-[17px] leading-snug mb-3">&ldquo;{card.query}&rdquo;</div>
                <div className="font-mono text-[9px] tracking-[0.06em] mb-4" style={{ color: "var(--mute)" }}>
                  {card.page} · {card.priority}
                </div>
                <p className="font-serif text-[13px] leading-relaxed" style={{ color: "var(--mute)" }}>
                  {card.reason}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
