# Admin Frontend Overhaul — Design Spec

Brainstormed 2026-07-06/07; decision-by-decision record in `2026-07-06-frontend-brainstorm-decisions.md`. Mockups in `.superpowers/brainstorm/*/content/` (visibility-board-v2, client-drilldown-v4, pages-tab-v2, approvals-inbox, run-detail).

## Goal

Rebuild the admin dashboard around the system's actual purpose: **improving AI-visibility metrics**. The frontend must reflect exactly what the backend stores — every stored artifact visible, nothing displayed that isn't stored. Admin-only; the client-facing interface stays reports-only and is out of scope.

## Framing decisions (the "why" behind every screen)

1. **Metrics first.** The number and its movement lead every surface; operations (cards, errors, schedules) appear as secondary badges/links. The hero metric is the client's **mention rate with competitive context** — not a composite score: `42% ▲+6 vs 61% KinderCare (#2 of 5)`.
2. **Long-lived states over the sequence.** Machine stages take ~5 minutes weekly; clients persist in: scheduled/idle, awaiting approval, live-and-measuring, error. The sequential rail appears only at per-run level, retrospectively.
3. **Mention vs citation, measured vs diagnostic.** Mention rate = you appear in the answer. Citation rate = share of mentions that also link your site (`prompt_scores.citation_rate`, conditional on mention). Citation *readiness* = the 0–100 per-page diagnostic (Step 4). All three appear under these exact names.
4. **No fabricated data.** Everything below names its table. Cut from v1 because nothing stores them: QA-drop counts, live per-step run progress, weak-match confirmation, on-demand brief generation, effect attribution ("+20 since change").

## Information architecture

```
Sidebar: BOARD (home) · APPROVALS · CLIENTS (list → drilldown) · REPORTS (existing, untouched)

Board ──click row──▶ Client drilldown ── tabs ──▶ OVERVIEW / QUERIES / PAGES / RUNS / CARDS / CONFIG
                                                     RUNS ──▶ Run detail
Approvals ◀── deep links from board badges, drilldown WAITING column, run detail
```

## Surface 1 — Home: the Visibility Board

One row per client, grid `[client+delta | head-to-head hero | biggest moves | sparkline+badge]`:

| Element | Source |
|---|---|
| Mention rate (large) | latest `tracker_runs.aggregate_mention_rate` |
| Delta vs previous cycle | latest minus previous `tracker_runs` |
| Top competitor rate + name, paired comparison bars, rank, gap-to-leader | `tracker_runs.competitor_scores` (top = highest aggregate rate) |
| Biggest moves (2 queries, before→after) | `prompt_scores` across last two runs, engine-averaged, largest absolute change |
| Sparkline (~6 cycles) | `aggregate_mention_rate` history |
| One ops badge | precedence: error (`pipeline_runs.status='error'`) > cards waiting (+age, `action_cards` pending by client) > measuring (implemented cards, next run pending) > healthy |

Header: portfolio rollup (N improving/declining/flat; total cards; errors). Footer: next scheduled runs (`GET /api/schedules`). Color rules: green/red = metric direction only; amber = needs-you; grey = neutral.

## Surface 2 — Client drilldown

**Header (all tabs):** visibility % huge + delta + "vs {top competitor}" + rank; second line: citation rate ("cited as source: 12% of mentions") with the mention/citation definition; next-run line. **Crawlability banner** when the latest `improvement_runs.crawlability_report.has_critical_blocker` is true: red strip naming the failing critical checks (robots_txt / cdn_blocks / js_rendering, each stored with status+detail) linking to the priority-0 card. Tabs stay live — the diagnosis below is the pre-fix baseline (backend deliberately continues past blockers; tracker data is always valid since visibility is measured from LLM answers, not the site).

**OVERVIEW tab:** timeline chart — aggregate visibility per cycle, every point labeled with its value, top competitor as dashed line (`competitor_scores` history). GSC panel (clicks/impressions/CTR per cycle, from `tracker_runs.gsc_*`) when configured.

**QUERIES tab:** query × cycle heat table. Per row: mention rate per cycle (color-scaled, engine-averaged from `prompt_scores`), stability label (existing Phase-3 computation), CITED %, matched PAGE + similarity (`query_page_matches`, latest run), top competitor + rate (`competitive_gaps`), WAITING (pending cards/briefs/community checks via `action_cards.query_id`). **Row expansion:** per-engine sub-rows — mentioned/cited flags, counts ("mentioned 4/5 · cited 2/5"), the response sentence containing the brand mention highlighted (extracted from `tracker_results.response_text`; representative response = most recent mentioned, else most recent), `citation_url` when cited, and on absence: competitors the answer recommended (`competitor_mentions`).

**PAGES tab:** per D13 — inventory + citation-readiness table, 9-check expansion with stored `detail` strings + schema errors + Sonnet quality, queries-served with weak matches display-only, content-gaps footer with VIEW BRIEF CARD buttons (brief exists only when `competitive_gap > 0`; otherwise "no brief — generated when a competitor leads").

**RUNS tab:** run list (date, status, cards generated) → Run detail (Surface 4). **CARDS tab:** this client's card history with statuses/verification. **CONFIG tab:** existing config surface (queries, competitors, CMS, schedule editing) relocated here.

## Surface 3 — Approvals inbox

- **One group = one client's run = one finalize action**, resuming that run's own `pipeline_runs.thread_id` (structural fix for the wrong-thread bug). Group header: card count, wait age, CMS consequence ("WORDPRESS — changes go live on approve" / "COPY_PASTE — manual apply").
- Metrics context strip per group ("why you're here: 18% ▼−4 · losing X by 40pts") and a "why" line per card (target query + gap).
- Card renderers by type: automated → before/after diff + code block + approve/reject/view page; `content_brief` → rendered brief document, accept-and-assign (no implementation); community check → search links (reddit + Google `site:reddit.com`), mark-done/thread-URL/skip; `fix_crawlability` → issue statement.
- Auto-approved cards: informational footer per group ("4 schema cards auto-approved — implement on finalize").
- **Rejections recorded:** finalize submits approved AND rejected ids; rejected cards get `status='rejected'` and never reappear. (Requires the approve route to accept both lists.)

## Surface 4 — Run detail

Retrospective view of one run: header (date, duration from `started_at`/`completed_at`, status), the **sequential rail** (segment states derived from run statuses — no live per-step progress exists in v1), six evidence tiles (measurement delta + worst gap; crawlability verdict expandable to the full report; pages inventoried; matched/weak/gaps; avg + lowest readiness score; cards generated/auto/waiting), the funnel line ("12 queries → 9 matched → 6 scored → 5 gaps → 11 cards → 4 auto + 7 to you"), footer linking forward ("re-measured by next run Jul 10") and to the run's cards in approvals. Sources: `improvement_runs` counters + `page_citation_scores`/`query_page_matches`/`action_cards` by `run_id`.

## Backend work in scope (all small)

1. **Community-check cards** (D5): remove the dead Google-scrape Reddit scout call; generate manual community-check cards directly from gap data (query, gap context, search URLs). Card fields fit the existing schema (`reddit_data`/brief-style jsonb or dedicated fields).
2. **Persist `preview_url`** in `run_implementation_node` (column exists from migration 008, never written) so PR/staging handoffs are queryable.
3. **Approve route accepts rejected ids** and marks them `status='rejected'`.
4. **Client-summary + drilldown derivations:** delta, top competitor, rank, biggest movers, heat-table series, expansion payloads — computed in **Next.js server components querying Supabase directly** (the existing pages' pattern; shared derivation helpers in `dashboard/lib/`). No new FastAPI endpoints.
5. Mention-sentence extraction (string processing around brand variations in `response_text`) — server-side helper.

## Removals

The legacy audit surfaces (`/admin/clients/[id]/audit`, `audit/[runId]`, `PageScoreRow`, `TriggerAuditButton`) read `audit_runs`/`page_scores`, which the new pipeline no longer writes — delete them. The old flat approvals page is replaced by Surface 3. The legacy `pillar`/`score` card fields stay in the DB (old rows) but the new UI reads `action_type`/`structural_score`.

## Explicitly deferred to v2

Effect attribution ("since change +N", needs `implemented_at`), weak-match confirm/override, on-demand brief generation, QA-drop counters, live per-step run progress, Outcomes analytics page, client-facing anything.

## Error/empty states

Client with no runs yet → board row shows "first run {date}" with muted hero. Query with <2 cycles → no delta/trend. Pages tab before any improvement run → empty state pointing at schedule. All lists paginate or cap sensibly (board sorted worst-delta-first; inbox oldest-first).

## Testing

Derivation functions (delta, top-competitor, movers, sentence extraction) unit-tested against fixture rows. Component tests for card renderers (each card type) and the heat table. Existing vitest setup in `dashboard/`.

## Visual language

Match the existing dashboard theme (dark ink, Georgia/serif display, mono uppercase labels, existing CSS variables). Mockups define hierarchy and content, not final polish.
