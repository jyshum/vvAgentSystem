# V1 Pipeline Final-Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist each improvement run's immutable route decision and effective technical check sets, use that marker for all dashboard presentation, validate technical-audit registries before network work, and correct count grammar.

**Architecture:** Migration 015 adds a constrained `run_mode` and typed `effective_check_sets` array to `improvement_runs`, defaulting every historical row to legacy and preventing later route mutation. The pipeline writes both fields in its initial insert, and dashboard helpers consume only `ImprovementRun.run_mode`; technical-audit child rows remain evidence rather than presentation discriminators. Small pure helpers own run/banner copy, while the runner constructs its registry before timestamps, URL normalization, or fetches.

**Tech Stack:** PostgreSQL/Supabase migrations, Python 3.11+, pytest, Next.js 16, React 19, TypeScript, Vitest, ESLint.

## Global Constraints

- Active V1 never falls back to matcher/scorer after audit error.
- Disabled/nonallowlisted legacy remains unchanged.
- No AI, auto-approval, or publishing is added.
- New V1 still writes no `query_page_matches` or `page_citation_scores`.
- Direct Pages routes and historical evidence remain.
- `foundation` is the only executable check set.
- Migration 015 is additive, defaults/backfills existing rows to legacy, and does not reinterpret historical audit-child rows.
- All regression tests are written and observed RED before production changes.

---

### Task 1: Write and capture the complete RED regression set

**Files:**

- Create: `agents/tests/test_improvement_run_migration.py`
- Modify: `agents/tests/test_improvement_pipeline.py`
- Modify: `agents/tests/technical_audit/test_runner.py`
- Modify: `dashboard/__tests__/run-presentation.test.ts`

**Interfaces:**

- Consumes: current pipeline insert payload, current child-derived `runPresentationMode`, current late registry construction.
- Produces: executable contracts for migration 015, persisted route values, four mode-classification cases, V1/legacy banner copy, singular/plural copy, and no-fetch invalid registry behavior.

- [ ] **Step 1: Add a migration contract test**

Create a pytest test that reads `supabase/migrations/015_improvement_run_mode.sql` and requires: `run_mode` with legacy default and `legacy`/`technical_v1` check, `effective_check_sets` as non-null `text[]` with empty-array default, mode/check-set consistency, and an update trigger that rejects changes to either routing field.

- [ ] **Step 2: Add pipeline insert assertions**

In the active V1 regression, require the initial `improvement_runs` insert to include:

```python
assert insert_payload["run_mode"] == "technical_v1"
assert insert_payload["effective_check_sets"] == ["foundation"]
```

In disabled and nonallowlisted regressions, require:

```python
assert insert_payload["run_mode"] == "legacy"
assert insert_payload["effective_check_sets"] == []
```

- [ ] **Step 3: Add runner no-fetch validation tests**

Parameterize `enabled_check_sets` as `("unsupported",)` and `()`, inject a fetcher that records calls, require `ValueError`, and assert the recorded call list remains empty.

- [ ] **Step 4: Replace child-derived presentation tests**

Require `runPresentationMode` to classify: legacy without audit, historical legacy with an audit child, completed technical V1, and technical V1 with no child. Add pure banner tests requiring the legacy approvals/fix-card CTA and a technical V1 Runs/evidence CTA with no fix-card or priority-zero language.

- [ ] **Step 5: Add count grammar tests**

Exercise zero, one, and plural technical checks, measured competitor leads, and manual cards. Require `1 technical check`, `1 measured competitor lead`, and `1 manual card`; explicitly reject `1 manual cards`.

- [ ] **Step 6: Run focused tests and capture RED**

Run:

```bash
cd agents
/Users/jshum/Desktop/code-folders/vvAgentSystem/agents/.venv/bin/python -m pytest \
  tests/test_improvement_run_migration.py \
  tests/test_improvement_pipeline.py \
  tests/technical_audit/test_runner.py -q

cd ../dashboard
npm test -- __tests__/run-presentation.test.ts
```

Expected: failures for missing migration 015 and insert fields, child-derived mode, missing banner helper/grammar, and fetcher calls made before invalid check-set rejection.

---

### Task 2: Persist immutable improvement-run routing

**Files:**

- Create: `supabase/migrations/015_improvement_run_mode.sql`
- Modify: `agents/src/improvement/pipeline.py`
- Modify: `dashboard/lib/improvement-types.ts`

**Interfaces:**

- Consumes: `technical_v1_active` and `policy.check_sets`, both computed before the existing insert.
- Produces: `ImprovementRunMode = "legacy" | "technical_v1"`, `TechnicalAuditCheckSet = "foundation"`, and immutable `ImprovementRun.run_mode` / `effective_check_sets` fields.

- [ ] **Step 1: Add migration 015**

Add non-null columns with historical-safe defaults:

```sql
run_mode text not null default 'legacy'
effective_check_sets text[] not null default '{}'::text[]
```

Add named checks for explicit modes and mode/check-set consistency. Add a `before update of run_mode, effective_check_sets` trigger that raises when either value changes. Do not query or rewrite `technical_audit_runs`.

- [ ] **Step 2: Persist route controls at insertion**

Extend the existing initial insert with:

```python
"run_mode": "technical_v1" if technical_v1_active else "legacy",
"effective_check_sets": list(policy.check_sets) if technical_v1_active else [],
```

Do not update either field later.

- [ ] **Step 3: Add dashboard types**

Add the two literal types and fields to `ImprovementRun` so presentation consumers cannot use an untyped string/JSON marker.

- [ ] **Step 4: Run focused agent tests GREEN**

Run the Task 1 agent command and require all tests to pass.

---

### Task 3: Make persisted mode control run and banner presentation

**Files:**

- Modify: `dashboard/lib/run-presentation.ts`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx`

**Interfaces:**

- Consumes: `Pick<ImprovementRun, "run_mode"> | null`.
- Produces: `runPresentationMode(improvementRun)`, `crawlabilityBannerPresentation(mode, clientId)`, and count-aware funnel strings.

- [ ] **Step 1: Change mode classification source**

Implement:

```ts
export function runPresentationMode(
  improvementRun: Pick<ImprovementRun, "run_mode"> | null,
): RunPresentationMode {
  return improvementRun?.run_mode === "technical_v1" ? "technical_v1" : "legacy";
}
```

No technical-audit child argument is accepted.

- [ ] **Step 2: Add count-aware and banner helpers**

Use a small `formatCount` helper in `buildRunFunnel`. Return technical banner copy that links to `/admin/clients/${clientId}/runs`, asks the operator to review run evidence/guidance, and contains no fix-card or priority-zero claims. Preserve the legacy `/admin/approvals` CTA and copy.

- [ ] **Step 3: Update the run page**

Pass `improvementRun` to `runPresentationMode`. A technical marker with no audit child renders `TECHNICAL AUDIT`, an unavailable neutral state, no legacy badge/matching/readiness wording, and a technical funnel. A legacy marker hides any older audit child and preserves legacy evidence/label.

- [ ] **Step 4: Update the client layout**

Select `run_mode` with the latest improvement run, derive mode from that persisted field, and render the pure banner presentation. Avoid other layout changes.

- [ ] **Step 5: Run focused dashboard tests GREEN**

Run:

```bash
cd dashboard
npm test -- __tests__/run-presentation.test.ts
npx eslint \
  lib/run-presentation.ts \
  lib/improvement-types.ts \
  app/admin/clients/'[id]'/layout.tsx \
  app/admin/clients/'[id]'/runs/'[runId]'/page.tsx \
  __tests__/run-presentation.test.ts
```

Expected: tests and lint pass.

---

### Task 4: Validate the technical registry before network work

**Files:**

- Modify: `agents/src/technical_audit/runner.py`

**Interfaces:**

- Consumes: `build_v1_registry(enabled_check_sets)`.
- Produces: one validated registry reused for `registry.run(context)`.

- [ ] **Step 1: Construct the registry first**

Make registry construction the first statement in `run_technical_audit`, before timestamp creation, URL normalization, profile processing, or fetches.

- [ ] **Step 2: Reuse the registry**

Replace the later `build_v1_registry(enabled_check_sets).run(context)` with `registry.run(context)`.

- [ ] **Step 3: Run focused runner tests GREEN**

Run:

```bash
cd agents
/Users/jshum/Desktop/code-folders/vvAgentSystem/agents/.venv/bin/python -m pytest tests/technical_audit/test_runner.py -q
```

Expected: all runner tests pass and both invalid-set cases record zero fetch calls.

---

### Task 5: Document, verify, self-review, report, and commit

**Files:**

- Modify: `docs/technical-audit-operations.md`
- Modify: `PROJECT_STATE.md`
- Create (untracked task artifact): `.superpowers/sdd/final-fix-report.md`

**Interfaces:**

- Consumes: cumulative diff from base `7955542` and all verification outputs.
- Produces: operator migration instructions, final evidence report, and coherent fix commit(s).

- [ ] **Step 1: Update operator migration behavior**

Document migration 015, legacy default/backfill, immutable marker/check sets, no child-row inference, and the requirement to apply 014 then 015 only in an approved development/staging environment. Update project state without claiming a remote migration was applied.

- [ ] **Step 2: Run focused GREEN suites**

Run all changed agent test files and the dashboard presentation tests.

- [ ] **Step 3: Run required full verification**

Run:

```bash
cd agents
/Users/jshum/Desktop/code-folders/vvAgentSystem/agents/.venv/bin/python -m pytest -q

cd ../dashboard
npm test
npx eslint <every changed dashboard TypeScript/TSX file>
npm run build

cd ..
git diff --check
```

- [ ] **Step 4: Self-review from base**

Inspect `git diff --stat 7955542`, `git diff 7955542 -- <changed files>`, and confirm every finding/global constraint is covered with no unrelated changes.

- [ ] **Step 5: Write the full report**

Record the root-cause evidence/hypothesis, exact RED and GREEN/full commands with outputs, migration behavior, changed files, cumulative self-review, and concerns in `.superpowers/sdd/final-fix-report.md`. Do not force-add `.superpowers`.

- [ ] **Step 6: Commit and re-verify repository state**

Stage only intended tracked files, commit with a coherent fix subject, then report the SHA/subject and whether the report remains intentionally untracked.
