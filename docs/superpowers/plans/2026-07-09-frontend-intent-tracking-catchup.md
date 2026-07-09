# Frontend Intent Tracking Catch-Up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the dashboard so it accurately presents backend intent/paraphrase tracking: one row per intent, `query_id`-based grouping, wording-aware drilldowns, deferred branded labeling, and visible query-set-change markers.

**Architecture:** Keep the existing dashboard structure and styling. Add intent identity at the data-fetch/type/helper layer, then let existing pages consume intent-keyed maps. Use `query_id` as the primary key and fall back to legacy query text only when old rows lack `query_id`.

**Tech Stack:** Next.js dashboard, TypeScript, Supabase server client, Vitest, existing CSS/Tailwind style conventions.

## Global Constraints

- Backend is the source of truth; do not change backend scoring in this plan.
- Branded prompts are deferred and not measured in current runs.
- Do not modify or stage `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md`.
- Treat `dashboard/app/mock-current/page.tsx` and the `dashboard/proxy.ts` mock auth exclusion as separate prior work; do not remove or commit it without an explicit decision.
- Preserve the existing dark editorial dashboard aesthetic. Do not introduce a new redesign, nested cards, or marketing-style sections.
- Prefer TDD: write or update the failing test before the production edit for each behavior.

---

## Current Dirty Work Checkpoint

There is already uncommitted partial implementation work. Before continuing implementation, review it rather than layering blindly on top.

Current dirty files relevant to this plan:

- `dashboard/__tests__/components/heat-table.test.tsx`
- `dashboard/__tests__/derive.test.ts`
- `dashboard/__tests__/stability.test.ts`
- `dashboard/app/admin/clients/[id]/layout.tsx`
- `dashboard/app/admin/clients/[id]/overview/page.tsx`
- `dashboard/app/admin/clients/[id]/pages/page.tsx`
- `dashboard/app/admin/clients/[id]/queries/page.tsx`
- `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`
- `dashboard/app/api/admin/query-detail/[clientId]/route.ts`
- `dashboard/app/api/admin/stability/[clientId]/route.ts`
- `dashboard/components/admin/AddClientModal.tsx`
- `dashboard/components/admin/HeatTable.tsx`
- `dashboard/components/admin/QueryBucketManager.tsx`
- `dashboard/components/admin/QueryExpansion.tsx`
- `dashboard/components/charts/TimelineChart.tsx`
- `dashboard/lib/derive.ts`
- `dashboard/lib/stability.ts`
- `dashboard/lib/types.ts`

Separate dirty files not part of this plan unless approved:

- `dashboard/proxy.ts`
- `dashboard/app/mock-current/page.tsx`
- `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md`

---

### Task 1: Baseline And Reconcile The Interrupted Diff

**Files:**
- Review only first: all dirty dashboard files above.
- Modify only if required by test failures in this task.

**Interfaces:**
- Consumes: existing partial implementation.
- Produces: a known baseline of what already passes and what still fails.

- [ ] **Step 1: Capture the current diff**

Run:

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git status --short
git diff --stat
```

Expected: dashboard catch-up files are dirty; unrelated improvement-pipeline spec is dirty and must remain untouched.

- [ ] **Step 2: Run focused tests already touched**

Run:

```bash
cd dashboard
npm test -- derive.test.ts stability.test.ts heat-table.test.tsx
```

Expected: these should pass if the interrupted helper/component changes are internally consistent. If they fail, fix only the tested intent-key behavior, then rerun the same command.

- [ ] **Step 3: Do not commit**

This task is a checkpoint only. Commit after the first coherent behavior task, not before the plan is approved.

---

### Task 2: Shared Intent-Key Helpers

**Files:**
- Modify: `dashboard/lib/derive.ts`
- Modify: `dashboard/lib/stability.ts`
- Modify: `dashboard/lib/types.ts`
- Test: `dashboard/__tests__/derive.test.ts`
- Test: `dashboard/__tests__/stability.test.ts`

**Interfaces:**
- Produces: shared behavior where prompt-score rows group by `query_id || query`.
- Later pages rely on these helpers returning one aggregate per intent.

- [ ] **Step 1: Ensure failing tests cover paraphrase grouping**

`dashboard/__tests__/derive.test.ts` must include a case where two rows have the same `query_id` and different `query` strings, and `engineAverageByQuery` returns one map entry keyed by that `query_id`.

`dashboard/__tests__/stability.test.ts` must include two runs where the same `query_id` appears with different `query` wording labels, and `computePromptStability` returns one result with `query_id` preserved.

- [ ] **Step 2: Run tests and verify failure if implementation is absent**

Run:

```bash
cd dashboard
npm test -- derive.test.ts stability.test.ts
```

Expected from a clean pre-catch-up frontend: failures showing query-text grouping splits one intent. If the current partial implementation already passes, record that in the final summary.

- [ ] **Step 3: Implement or verify helper behavior**

Required behavior:

- `ScoreRow` accepts `query_id?: string | null`.
- `engineAverageByQuery(rows)` groups by `row.query_id || row.query`.
- `biggestMovers(latest, previous)` compares by `query_id || query` and displays the latest label.
- `aggregatePromptScores(promptScores, runs)` groups by `query_id || query`, stores `query_id`, and keeps a display `query`.
- `computePromptStability(runsData)` returns `query_id: string | null`.
- `TrackerRun.bucket_scores` uses `intent_count`, not `count`.
- `TrackerRun` includes nullable `query_set_signature` and `query_set_changed`.

- [ ] **Step 4: Verify**

Run:

```bash
cd dashboard
npm test -- derive.test.ts stability.test.ts
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Only after approval to proceed:

```bash
git add dashboard/lib/derive.ts dashboard/lib/stability.ts dashboard/lib/types.ts dashboard/__tests__/derive.test.ts dashboard/__tests__/stability.test.ts
git commit -m "feat: dashboard groups prompt metrics by intent id"
```

---

### Task 3: Intent Heat Table And Latest-Run Expansion

**Files:**
- Modify: `dashboard/app/admin/clients/[id]/queries/page.tsx`
- Modify: `dashboard/components/admin/HeatTable.tsx`
- Modify: `dashboard/components/admin/QueryExpansion.tsx`
- Modify: `dashboard/app/api/admin/query-detail/[clientId]/route.ts`
- Test: `dashboard/__tests__/components/heat-table.test.tsx`

**Interfaces:**
- Consumes: `query_id`-keyed helper output from Task 2.
- Produces: one heat row per intent and expansion fetches by intent id.

- [ ] **Step 1: Update component tests**

The heat table fixture must include:

```ts
{
  queryId: "intent-1",
  query: "best daycare software",
  paraphrases: ["top childcare apps", "daycare management tools"],
  version: 2,
  bucket: "awareness",
  cells: [{ runId: "run-1", ranAt: "2026-07-09T00:00:00Z", rate: 0.5, querySetChanged: true }],
  stability: "gaining",
  citedPct: 0.25,
  competitor: null,
  page: null,
  waitingActions: 0
}
```

Assertions should verify that `INTENT`, `3 WORDINGS`, `V2`, and the changed-cycle marker render.

- [ ] **Step 2: Run the heat table test**

Run:

```bash
cd dashboard
npm test -- heat-table.test.tsx
```

Expected from old frontend: failure because rows lack intent metadata.

- [ ] **Step 3: Implement or verify data fetching**

In `queries/page.tsx`:

- Select `tracker_runs.id, ran_at, query_set_changed`.
- Select `queries.id, prompt_text, bucket, paraphrases, version`.
- Select `prompt_scores.run_id, query_id, query, bucket, llm, mention_rate, citation_rate, avg_mention_level`.
- Select `competitive_gaps.query_id, query, competitor_data`.
- Select `query_page_matches.query_id, query_text, match_type, matched_page_url, similarity_score`.
- Build row keys from `query_id || query`.
- Use `queries.prompt_text` as the display label when metadata exists.

- [ ] **Step 4: Implement or verify expansion**

In `QueryExpansion`, send `query_id` when available. In `query-detail` API:

- Accept either `query_id` or `query`.
- Filter `tracker_results` by `query_id` when present.
- Include distinct result `query` values as `wordings` per engine.

- [ ] **Step 5: Verify**

Run:

```bash
cd dashboard
npm test -- heat-table.test.tsx
```

Expected: pass.

- [ ] **Step 6: Commit**

Only after approval to proceed:

```bash
git add 'dashboard/app/admin/clients/[id]/queries/page.tsx' dashboard/components/admin/HeatTable.tsx dashboard/components/admin/QueryExpansion.tsx 'dashboard/app/api/admin/query-detail/[clientId]/route.ts' dashboard/__tests__/components/heat-table.test.tsx
git commit -m "feat: show visibility heat table by intent"
```

---

### Task 4: Query-Set Drift Markers

**Files:**
- Modify: `dashboard/components/charts/TimelineChart.tsx`
- Modify: `dashboard/app/admin/clients/[id]/overview/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`

**Interfaces:**
- Consumes: `tracker_runs.query_set_changed`.
- Produces: subtle visual markers where trend continuity is broken.

- [ ] **Step 1: Add a focused visual/logic test if one already exists**

If `TimelineChart` has an existing test file, add a case asserting that a changed point renders an asterisk label. If no chart test exists, keep this task verified through build and manual review because the current repo may not have chart test scaffolding.

- [ ] **Step 2: Implement or verify markers**

Required behavior:

- `TimelinePoint` supports `querySetChanged?: boolean`.
- Changed points render amber and slightly larger.
- Label appends `*`.
- Overview footnote appears if any run changed.
- Client header and run detail show compact `query set changed` badges.

- [ ] **Step 3: Verify**

Run:

```bash
cd dashboard
npm run lint
npm run build
```

Expected: lint and build pass.

- [ ] **Step 4: Commit**

Only after approval to proceed:

```bash
git add dashboard/components/charts/TimelineChart.tsx 'dashboard/app/admin/clients/[id]/overview/page.tsx' 'dashboard/app/admin/clients/[id]/layout.tsx' 'dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx
git commit -m "feat: mark query-set changes in dashboard trends"
```

---

### Task 5: Secondary Views And Reports Use Intent Identity

**Files:**
- Modify: `dashboard/app/admin/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/pages/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/reports/[reportId]/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/reports/[reportId]/view/page.tsx`
- Modify: `dashboard/app/admin/reports/[id]/page.tsx`
- Modify: `dashboard/components/report/QueryResultsTable.tsx`
- Possibly modify: `supabase/schema.sql` only if the `tracker_results_client` view truly omits required fields for deployed reports.

**Interfaces:**
- Consumes: intent-keyed `prompt_scores`, `competitive_gaps`, and `tracker_results`.
- Produces: reports and secondary pages that do not split one intent into multiple wording rows.

- [ ] **Step 1: Inspect current selects**

Run:

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
rg "prompt_scores|competitive_gaps|tracker_results_client|tracker_results|QueryResultsTable" dashboard/app dashboard/components/report supabase/schema.sql
```

Expected: identify every remaining text-keyed select/grouping.

- [ ] **Step 2: Update report/result fetches**

Required behavior:

- Any prompt-score select that feeds query movement or stability includes `query_id`.
- Any competitive-gap select includes `query_id`.
- Any tracker-results select that feeds grouped query tables includes `query_id`, `bucket`, `run_number`, `mention_level`, and `mention_level_label` when the component expects those fields.
- `QueryResultsTable` groups by `query_id || query` and displays the canonical/latest label.

- [ ] **Step 3: Validate `tracker_results_client`**

If `dashboard/app/admin/reports/[id]/page.tsx` depends on `tracker_results_client.select("*")`, verify the view exposes `query_id` and `bucket`. If it does not, update the view in `supabase/schema.sql` and create a migration in a separate backend/schema commit, or document that this report remains legacy until the view migration is approved.

- [ ] **Step 4: Verify**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
```

Expected: all dashboard tests pass, lint passes, build passes.

- [ ] **Step 5: Commit**

Only after approval to proceed:

```bash
git add dashboard/app/admin/page.tsx 'dashboard/app/admin/clients/[id]/pages/page.tsx' 'dashboard/app/admin/clients/[id]/reports/[reportId]/page.tsx' 'dashboard/app/admin/clients/[id]/reports/[reportId]/view/page.tsx' 'dashboard/app/admin/reports/[id]/page.tsx' dashboard/components/report/QueryResultsTable.tsx
git commit -m "feat: use intent identity across dashboard reports"
```

If a schema/view migration is needed, commit it separately with only schema files staged.

---

### Task 6: Config Copy And Deferred Branded State

**Files:**
- Modify: `dashboard/components/admin/QueryBucketManager.tsx`
- Modify: `dashboard/components/admin/AddClientModal.tsx`

**Interfaces:**
- Consumes: `Query.paraphrases` type from Task 2.
- Produces: config surfaces that show wordings and label branded as deferred.

- [ ] **Step 1: Verify current copy**

Search:

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
rg "tracked separately|Branded Prompts|branded" dashboard/components/admin dashboard/app/admin/clients
```

Expected: no visible copy should claim branded is actively tracked separately.

- [ ] **Step 2: Implement or verify copy**

Required visible copy:

- Query manager intro: `Awareness and consideration intents are measured. Branded monitoring is deferred.`
- Branded bucket detail: `Deferred - not measured in current runs`.
- Add-client branded label: `Branded Prompts - Deferred`.

Use ASCII hyphen in code unless an existing file already uses a typographic dash.

- [ ] **Step 3: Show wording metadata**

In query rows, show `N WORDINGS` when `query.paraphrases.length > 0`.

- [ ] **Step 4: Verify**

Run:

```bash
cd dashboard
npm run lint
npm run build
```

Expected: pass.

- [ ] **Step 5: Commit**

Only after approval to proceed:

```bash
git add dashboard/components/admin/QueryBucketManager.tsx dashboard/components/admin/AddClientModal.tsx
git commit -m "feat: label branded prompts as deferred"
```

---

### Task 7: Final Verification And Mock Route Decision

**Files:**
- No production file changes unless verification finds failures.
- Optional decision files: `dashboard/app/mock-current/page.tsx`, `dashboard/proxy.ts`.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: a verified, reviewable frontend catch-up branch.

- [ ] **Step 1: Full dashboard verification**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
```

Expected: all pass.

- [ ] **Step 2: TypeScript check**

Run:

```bash
cd dashboard
npx tsc --noEmit
```

Expected: pass. If it fails only because of stale generated `.next/types` duplicate files, record the exact filenames and use `npm run build` as the TypeScript gate for this branch. Do not delete generated files unless explicitly approved in the moment.

- [ ] **Step 3: Decide mock route**

Ask the user whether to keep or remove:

- `dashboard/app/mock-current/page.tsx`
- the `/mock-current` auth bypass in `dashboard/proxy.ts`

Do not bundle this decision into the intent catch-up commit without approval.

- [ ] **Step 4: Final status**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: only intentionally uncommitted files remain, or the branch is clean except unrelated user edits.

---

## Self-Review

- Spec coverage: this plan covers helper grouping, heat table, expansion, drift markers, reports, config copy, and verification.
- Main risk: Task 5 may expose a schema/view mismatch in `tracker_results_client`; that needs a deliberate decision because it crosses back into DB schema.
- Process correction: no more production-code edits should happen until this spec and plan are approved.
- Placeholder scan: no task is allowed to say "fix as needed" without an exact target behavior; any discovered failure must be reduced to a concrete diff before committing.
