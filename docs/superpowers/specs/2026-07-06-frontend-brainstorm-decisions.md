# Frontend Overhaul — Running Decisions Log

Working document for the admin frontend brainstorm (started 2026-07-06). Feeds the eventual design spec. Newest decisions at the bottom.

## D1 — Admin-only scope
The overhaul is for the agency team only. Client-facing interface is deferred; clients keep the existing reports and nothing else. No pipeline visibility for clients.

## D2 — The pipeline's long-lived states drive the UI, not the sequence
Machine stages (tracker → GSC → improvement) take ~5 minutes once per cycle. At any moment nearly every client is in one of the states that actually persist:
- **Scheduled / idle** (days) — waiting for next cycle
- **Awaiting approval** (hours–days) — waiting on the team
- **Live & measuring** (up to a full cycle) — changes implemented; outcome resolves at the next tracker run
- **Error**

A full sequential board as the home page is over-designed for steady state. The sequential visualization belongs at the **per-run level**: a live progress rail during the ~5-minute execution window, and a retrospective "what did this run do" afterward.

## D3 — Implementation is a fan-out with human handoffs, and they must be visible
Approved cards end in different states per CMS:
| CMS | End state |
|---|---|
| WordPress / Shopify | Live immediately → auto-verified (verification badge) |
| GitHub | PR opened → **team must merge** |
| Webflow | Staged → **team must publish** |
| copy_paste | **Manual to-do for the team** |
These handoffs are currently invisible and must appear in whatever "waiting on you" surface the UI has.

## D4 — Mental model for the whole system (5 pieces)
Setup → Run (measure + diagnose/propose) → Approve → Implement → Re-measure. The "big pipeline" is the Run and it's fully automatic; the team only sees its output. UI language should follow this model. ("Baseline" is not a system concept — first run is just the first measurement.)

## D5 — Automated Reddit scout is scrapped (2026-07-06)
Findings from live testing + research:
- Unauthenticated `reddit.com/*.json` endpoints return 403 for all user agents, including browser UAs, even from residential IPs. Dead.
- The shipped Google-scrape approach gets CAPTCHA'd from datacenter IPs. Effectively dead in production.
- OAuth is the only working route, but app registration review takes ~1 week and paid-agency use sits in Reddit's commercial gray zone (enterprise pricing starts ~$12k/mo).

**Decision:** no automated Reddit data. The pipeline still generates a **manual "community check" card per losing query** containing: the query + competitive gap context, pre-built search links (reddit search + Google `site:reddit.com`), guidance on what to look for, and a field to record the engaged thread URL / mark done. Humans do the searching and all commenting (drip pace — mass promotional commenting risks shadowbans and public astroturfing callouts, which is GEO poison).

**Backend follow-up (small):** remove the scraper call from the improvement pipeline; generate community-check cards directly from gap data.

## D6 — Metrics-first framing (the core decision)
The system exists to improve visibility metrics; everything else is a lever. The frontend leads with metrics, ops surfaces are secondary. The current frontend fails this: metrics are buried per-client/per-run, no cross-client rollup, no deltas, no action→outcome linkage.

## D7 — Home page: the Visibility Board (APPROVED 2026-07-06)
One row per client, strict hierarchy:
1. **Hero: head-to-head** — client mention rate in large type VS top competitor's rate (`42% VS 61% KINDERCARE`), paired comparison bars, delta since last cycle, rank + gap-to-leader line. (Share of voice = mention rate + competitor context; not a composite score.)
2. **Biggest moves** — the 2 queries that moved most this cycle, with before→after rates.
3. **Sparkline** (rate across last ~6 cycles) + **one ops badge** (cards waiting / measuring / error / healthy).
Portfolio rollup in the header (N improving / declining / flat · cards to review · errors). Color discipline: green/red = metric direction only, amber = needs-you, grey = neutral. Everything else (schedules, query counts, run details) lives one click deeper. Visual aesthetics to match existing dashboard at implementation time; mockups settle hierarchy/content only.

## D8 — Client drilldown page (APPROVED 2026-07-07)
Hierarchy top to bottom:
1. **Hero:** visibility % huge (~84px) + delta + "vs {top competitor} {rate}" + rank. Second-tier stat: **citation rate** ("cited as source: 12% of mentions"), with the mention-vs-citation definition inline. Citation rate = share of *mentions* that also linked the client's site (conditional on mention — from `prompt_scores.citation_rate`).
2. **Timeline chart:** aggregate visibility per cycle, every point labeled with its number, top competitor as dashed comparison line. Data: `tracker_runs.aggregate_mention_rate` + `competitor_scores` per run.
3. **Query × cycle heat table:** per-query mention rate per cycle (color-scaled cells), stability label (existing Phase-3 computation), CITED column, top competitor per query, WAITING column (pending cards/briefs/community checks via `action_cards.query_id`).
4. **Row expansion:** per-engine sub-rows with mentioned/cited flags, counts (e.g. "mentioned 4/5 · cited 2/5"), the actual response sentence with the brand mention highlighted (extracted from `tracker_results.response_text`), cited URL when present. When client is absent: show which competitors the answer recommended instead (from `competitor_mentions`). Representative response rule: most recent mentioned response, else most recent.
Tabs: OVERVIEW / QUERIES / RUNS / CARDS / CONFIG (setup lives in CONFIG, out of the daily path).

## D9 — Deferred to v2 (2026-07-07)
- **Effect attribution** ("this change → +20 on its query"): needs an `implemented_at` timestamp (migration) and a before/after derivation, phrased as "since change" (correlation, not causation). Not in v1.
- The lever column in v1 shows only *what's waiting* (existing data), not measured effects.
- Data provenance audit confirmed everything else on both approved screens maps to existing tables (`tracker_runs`, `prompt_scores`, `competitive_gaps`, `stability`, `action_cards`, `tracker_results`); the only derivations needed are: cycle delta, top-competitor pick, biggest movers, and gap-direction phrasing — one client-summary endpoint.

## Open questions (not yet decided)
- Information architecture: what is the home page; where runs, approvals, client config live. "Unified run stream" concept explored but not accepted — felt disconnected from scheduling and unclear in purpose.
- Run detail view layout (the sequential rail + step artifacts + cards).
- Approvals inbox layout (must fix: per-client/run grouping, wrong-thread resume bug, rejected-card persistence, rendering of briefs/community cards/verification).
- How outcomes (mention-rate before/after per implemented change) get displayed.
