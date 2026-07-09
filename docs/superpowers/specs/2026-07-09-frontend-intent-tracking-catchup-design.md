# Frontend Intent Tracking Catch-Up - Design Spec

**Date:** 2026-07-09
**Status:** Draft after interrupted implementation
**Scope:** Dashboard frontend and dashboard API routes only. Backend intent/paraphrase tracking from `2026-07-08-intent-paraphrase-tracking-design.md` is already implemented on branch `intent-tracking`.

---

## Goal

Catch the dashboard up to the backend's current visibility model: the measured unit is an **intent** (`queries.id`), each intent can have several **wordings** (`prompt_text + paraphrases`), all primary metrics are non-branded, branded prompts are **deferred**, and runs can mark a **query-set change** when trend comparability breaks.

This is not a new product redesign. The UI should keep the existing dark editorial dashboard language while correcting labels, grouping, fetches, and drilldowns so the dashboard does not misrepresent backend data.

## Original Problem

The backend now stores and computes visibility differently than the old frontend assumed:

- `prompt_scores` and `competitive_gaps` are intent-level rows keyed by `query_id`.
- `tracker_results.query` is the specific wording fired, not always the canonical prompt.
- The canonical label for display is `queries.prompt_text`.
- `queries.paraphrases` explains how many sampled wordings belong to an intent.
- `tracker_runs.query_set_changed` flags cycles that should not be read as direct trend continuity.
- `tracker_runs.bucket_scores` now uses `intent_count`, not `count`.
- Branded prompts are intentionally not measured right now; the UI must label them as deferred, not tracked separately.

The current frontend still has several query-text assumptions. Those are now wrong because two rows for the same intent can have different `query` wording strings.

## Current Work Already Started

Before this spec was written, partial dashboard changes were made and are currently uncommitted. They must be reviewed against this spec before being kept.

Started changes:

- `dashboard/lib/derive.ts`: `engineAverageByQuery` and `biggestMovers` started grouping by `query_id || query`.
- `dashboard/lib/stability.ts`: prompt stability started grouping by `query_id || query`.
- `dashboard/components/admin/HeatTable.tsx`: heat rows now carry `queryId`, `paraphrases`, `version`, and query-set-change markers.
- `dashboard/components/admin/QueryExpansion.tsx` and `dashboard/app/api/admin/query-detail/[clientId]/route.ts`: expansion can fetch by `query_id` and list sampled wordings.
- `dashboard/app/admin/clients/[id]/queries/page.tsx`: started selecting `query_id`, `paraphrases`, `version`, and `query_set_changed`.
- `dashboard/components/admin/QueryBucketManager.tsx` and `dashboard/components/admin/AddClientModal.tsx`: branded copy partially changed to deferred.
- `dashboard/components/charts/TimelineChart.tsx`, overview, layout, and run detail pages: started displaying query-set-change markers.
- `dashboard/app/admin/clients/[id]/pages/page.tsx`: started matching competitive gaps by `query_id`.
- Tests started in `dashboard/__tests__/derive.test.ts` and `dashboard/__tests__/stability.test.ts`.

Separate prior mock work:

- `dashboard/app/mock-current/page.tsx` and a `dashboard/proxy.ts` auth exclusion were added for the fake-data mockup request. This is unrelated to the catch-up and should be either kept as a dev-only route or removed deliberately in a separate decision.

Known dirty file to avoid:

- `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md` has unrelated user/accidental edits and must not be staged, reverted, or modified as part of this work.

## Desired User Experience

### 1. Dashboard Metrics Speak in Intents

Anywhere the dashboard currently says "query" while showing intent-level metrics should use "intent" in visible labels where it improves clarity:

- Heat table first column: `INTENT`.
- Query management can still be titled "Query Buckets" if that is the product language, but body copy should explain that awareness and consideration intents are measured.
- Per-row metadata should expose the backend model without adding clutter: `N WORDINGS`, optional `V<version>`.

The visual style stays consistent with the current revamp: restrained monochrome, serif labels for human-readable names, small mono metadata, thin borders, no new card-heavy marketing layout.

### 2. Grouping Uses `query_id`

Frontend aggregation must prefer `query_id` wherever backend rows can include it.

Required grouping rules:

- `prompt_scores`: group by `query_id || query`.
- `competitive_gaps`: group by `query_id || query`.
- `query_page_matches`: match by `query_id` first, then fallback to `query_text`.
- `tracker_results` drilldown: filter by `query_id` when available; only fallback to exact `query`.
- Display label: prefer `queries.prompt_text` for that `query_id`; fallback to latest/canonical score query if old data lacks `query_id`.

The fallback is only for old or incomplete data. New data should have `query_id`.

### 3. Expansion Shows Wording Sampling

The heat table expansion should answer: "What actually got sampled for this intent?"

Minimum behavior:

- Fetch the latest run's `tracker_results` by `query_id`.
- Aggregate per engine as the current expansion already does.
- Include distinct `tracker_results.query` values as `wordings`.
- Show a small `N wordings sampled` line when more than one wording exists.

This is intentionally lightweight. No full paraphrase editor belongs in the expansion.

### 4. Drift Is Visible, But Not Overstated

If `tracker_runs.query_set_changed` is true:

- The timeline point gets a subtle amber marker and `*`.
- Overview shows a short footnote that the query set changed and that point is not directly comparable.
- Client header and run detail can show a compact `query set changed` badge.
- Heat table cycle headers can mark changed cycles with `*`.

Do not compute "same-intents-only" trends in this spec. The backend preserves enough data for that later, but this catch-up only labels trend breaks.

### 5. Branded Is Deferred

The frontend should not imply branded prompts are currently measured. Copy should say:

- `Branded` bucket detail: `Deferred - not measured in current runs`.
- Header/body copy: `Awareness and consideration intents are measured. Branded monitoring is deferred.`

For now, branded rows may remain visible/configurable because the enum and DB path exist, but measured dashboard views should treat branded as absent/deferred. If disabling branded input is desired, that should be a separate product decision.

### 6. Reports and Secondary Views Must Not Regress

The catch-up cannot stop at the main heat table. Any page that reads prompt-level/run-level results must either:

- select and use `query_id`, or
- be explicitly documented as legacy/fallback.

Known areas to inspect:

- `dashboard/app/admin/page.tsx`
- `dashboard/app/admin/clients/[id]/reports/[reportId]/page.tsx`
- `dashboard/app/admin/clients/[id]/reports/[reportId]/view/page.tsx`
- `dashboard/components/report/QueryResultsTable.tsx`
- `dashboard/app/admin/reports/[id]/page.tsx`
- Supabase `tracker_results_client` view shape in `supabase/schema.sql`

The report table should group result rows by intent, not wording, when `query_id` is available.

## Non-Goals

- No backend scoring changes.
- No automated intent/paraphrase generation.
- No branded reputation monitoring.
- No same-intents-only trend calculation.
- No broad dashboard redesign.
- No unrelated cleanup of the improvement pipeline spec.

## Acceptance Criteria

- Frontend aggregations and stability calculations group paraphrase rows under one intent using `query_id`.
- The main client query/intent heat table displays one row per intent, not one row per wording.
- Heat table expansion fetches by `query_id` and shows sampled wording count.
- Query-set-change markers appear on timeline, heat table cycle headers, client header, and run detail.
- Branded bucket copy says deferred and does not claim active measurement.
- Reports and secondary views either use `query_id` or have an explicit fallback path for legacy rows.
- Dashboard types match backend shape: `bucket_scores.*.intent_count`, `query_set_signature`, `query_set_changed`, `Query.paraphrases`, and result/query rows with optional `query_id`.
- Verification passes or any blocker is documented with exact command output.

## Self-Review Flags

- The interrupted implementation likely compiles only partially; no full `tsc`, lint, build, or full dashboard test run has been completed after the broader page edits.
- Direct `npx tsc --noEmit` previously hit stale `.next/types` duplicate generated files. The plan should either clean generated `.next` safely or use `npm run build` as the TypeScript gate and document the reason.
- The mock-current route is separate work. It should not be mixed into the frontend catch-up commit unless the user explicitly wants to keep it.
- Report pages and `tracker_results_client` are the highest-risk misses because they are easy to overlook while the main dashboard appears fixed.
- The partial implementation changed copy and UI before the spec existed. Those changes should be reviewed against this spec before proceeding.
