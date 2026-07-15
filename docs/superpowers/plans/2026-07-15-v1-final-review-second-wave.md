# V1 Final-Review Second-Wave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve technical checklist evidence on historical hybrid runs without changing parent-mode vocabulary, and make the canonical fresh-install schema carry the complete immutable improvement-run routing contract.

**Architecture:** Add one focused `RunTechnicalAuditEvidence` wrapper that renders the real `TechnicalAuditChecklist` whenever a child exists and adds a historical label only when the authoritative parent mode is legacy. Keep all run-page tiles, funnel vocabulary, and unavailable behavior driven by `improvement_runs.run_mode`. Mirror migration 015 directly into `schema.sql` at fresh-install table/function/trigger locations, including explicit cleanup ordering.

**Tech Stack:** React 19, TypeScript, Testing Library, Vitest, PostgreSQL/Supabase SQL, Python 3.11+, pytest.

## Global Constraints

- `improvement_runs.run_mode` remains authoritative for vocabulary and routing.
- A technical-audit child controls evidence visibility only; it never reclassifies its parent.
- Technical V1 without a child remains technical/unavailable and exposes no legacy terminology.
- Migration 015 is not weakened or applied to any database.
- No unrelated run-page, pipeline, rollout, or external-service behavior changes.
- Tests must be observed RED before production files change.

---

### Task 1: Render historical hybrid checklist evidence

**Files:**

- Create: `dashboard/__tests__/components/run-technical-audit-evidence.test.tsx`
- Create: `dashboard/components/runs/RunTechnicalAuditEvidence.tsx`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`

**Interfaces:**

- Consumes: `mode: RunPresentationMode`, `run: TechnicalAuditRun | null`, and `results: TechnicalAuditResult[]`.
- Produces: `RunTechnicalAuditEvidence`, which returns `null` without a child, renders ordinary technical evidence for technical V1, and prefixes legacy child evidence with `HISTORICAL TECHNICAL CHECKLIST`.

- [ ] **Step 1: Write the render regression first**

Render the real checklist through the wished-for wrapper with a completed child/result fixture. Assert:

```tsx
expect(screen.getByText("HISTORICAL TECHNICAL CHECKLIST")).toBeTruthy();
expect(screen.getByText("Canonical declaration is missing")).toBeTruthy();
```

For technical mode, assert ordinary `Technical audit` evidence and no historical label. For a null child, assert no checklist or historical label.

- [ ] **Step 2: Capture RED**

Run:

```bash
cd dashboard
npm test -- __tests__/components/run-technical-audit-evidence.test.tsx
```

Expected: collection fails because `RunTechnicalAuditEvidence` does not exist.

- [ ] **Step 3: Implement the minimal wrapper**

Create a component with this boundary:

```tsx
export function RunTechnicalAuditEvidence({
  mode,
  run,
  results,
}: {
  mode: RunPresentationMode;
  run: TechnicalAuditRun | null;
  results: TechnicalAuditResult[];
})
```

Return `null` when `run` is null. Otherwise render the historical label only for `mode === "legacy"`, followed by the existing real `TechnicalAuditChecklist`.

- [ ] **Step 4: Integrate without changing presentation mode**

Replace the run page's technical-only checklist conditional with:

```tsx
<RunTechnicalAuditEvidence
  mode={presentationMode}
  run={technicalAudit.run}
  results={technicalAudit.results}
/>
```

Do not change the legacy badge, tiles, funnel, mode helper, or technical no-child unavailable copy.

- [ ] **Step 5: Run focused GREEN and lint**

Run:

```bash
cd dashboard
npm test -- \
  __tests__/components/run-technical-audit-evidence.test.tsx \
  __tests__/components/technical-audit-checklist.test.tsx \
  __tests__/run-presentation.test.ts
npx eslint \
  components/runs/RunTechnicalAuditEvidence.tsx \
  app/admin/clients/'[id]'/runs/'[runId]'/page.tsx \
  __tests__/components/run-technical-audit-evidence.test.tsx
```

Expected: all focused tests and lint pass.

---

### Task 2: Mirror migration 015 into the canonical schema

**Files:**

- Modify: `agents/tests/test_improvement_run_migration.py`
- Modify: `supabase/schema.sql`

**Interfaces:**

- Consumes: migration 015's exact mode/check-set constraints, immutability function/trigger, and comments.
- Produces: one contract test applied to both SQL sources, plus canonical fresh-install drop/create ordering.

- [ ] **Step 1: Extend the SQL contract test first**

Parameterize the existing contract across:

```python
[MIGRATION, CANONICAL_SCHEMA]
```

For both normalized SQL sources require both columns/defaults, named mode and consistency constraints, the immutability function/trigger, and both comments. For `schema.sql`, additionally require `drop function if exists public.prevent_improvement_run_route_mutation() cascade` and verify table creation precedes function creation, which precedes trigger creation.

- [ ] **Step 2: Capture RED**

Run:

```bash
cd agents
/Users/jshum/Desktop/code-folders/vvAgentSystem/agents/.venv/bin/python \
  -m pytest tests/test_improvement_run_migration.py -q
```

Expected: the migration case passes and canonical-schema case fails because the routing contract is absent.

- [ ] **Step 3: Update canonical fresh-install SQL**

Add `run_mode` and `effective_check_sets` with the same defaults and named constraints inside `create table public.improvement_runs`. Add explicit function cleanup in the drop block. After the table exists, add the same `create or replace function`, `create trigger`, and column comments as migration 015.

- [ ] **Step 4: Run schema contract GREEN**

Run the Task 2 focused pytest command and require all parameter cases to pass.

---

### Task 3: Verify, review, report, and commit

**Files:**

- Append: `.superpowers/sdd/final-fix-report.md` (ignored; never force-add)

**Interfaces:**

- Consumes: the second-wave RED/GREEN/full outputs and cumulative diff from `5098cb6`.
- Produces: one coherent commit and appended final-review evidence.

- [ ] **Step 1: Run combined focused GREEN**

Run both new/changed test files together with the existing presentation/checklist tests.

- [ ] **Step 2: Run required full verification**

Run full agents, full dashboard, changed-file lint, `npm run build`, and `git diff --check`.

- [ ] **Step 3: Self-review the complete second-wave diff**

Confirm parent mode still drives every legacy/technical term; child existence drives only checklist evidence; migration 015 is unchanged; fresh-install SQL has valid drop/table/function/trigger order; no external state changed.

- [ ] **Step 4: Commit tracked files**

Stage only the plan, tests, component/page integration, and canonical schema. Commit with a focused fix subject. Do not stage `.superpowers`.

- [ ] **Step 5: Append the final report**

Append the second-wave root causes, exact RED/GREEN/full outputs, files, commit, self-review, and concerns to `.superpowers/sdd/final-fix-report.md`.
