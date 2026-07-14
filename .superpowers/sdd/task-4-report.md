# Task 4 Report: Remove page-matching claims from the primary query view

## Status

Implemented in the three owned dashboard files and committed with the requested report.

## Files changed

- `dashboard/app/admin/clients/[id]/queries/page.tsx`
- `dashboard/components/admin/HeatTable.tsx`
- `dashboard/__tests__/components/heat-table.test.tsx`

## Verification evidence

### RED

After updating the HeatTable test fixture and expectations first:

```text
npm test -- __tests__/components/heat-table.test.tsx
Test Files  1 failed (1)
Tests       1 failed | 1 passed (2)
Failure: expected PAGE query result to be null, but the current table rendered PAGE.
```

This was the expected failure proving the old page-match presentation was still active.

### GREEN and changed-file lint

```text
npm test -- __tests__/components/heat-table.test.tsx
Test Files  1 passed (1)
Tests       2 passed (2)

npx eslint components/admin/HeatTable.tsx app/admin/clients/'[id]'/queries/page.tsx __tests__/components/heat-table.test.tsx
exit code 0
```

### Full dashboard suite

```text
npm test
Test Files  13 passed (13)
Tests       91 passed (91)
```

Additional `git diff --check` completed without whitespace errors.

## Implementation summary

- Removed the `page` field and page pathname/similarity/WEAK rendering from `HeatTable`.
- Reduced the grid template to the four trailing evidence columns: stability, cited, top competitor, and cards.
- Removed the latest `improvement_runs` lookup and `query_page_matches` lookup from the query page loader.
- Removed `latestImprovementRunId`, `matches`, `pageByQuery`, and row-level `page` construction.
- Retained tracked-query history, citation rate, stability, competitor visibility, paraphrases, and pending-card counts/deep-links.

## Self-review

- Confirmed no `PAGE`, similarity, or `WEAK` presentation remains in the primary query table.
- Confirmed the `TOP COMPETITOR` and `CARDS` columns remain in the table and their loader data paths remain intact.
- Confirmed pending-card approval links remain covered by the focused test.
- Confirmed no legacy Pages route files were modified.
- Confirmed all changes stay within the requested ownership, with this report as the explicitly requested documentation file.

## Concerns

No blocking concerns. The loader’s Supabase query wiring is not directly unit-tested in the existing focused component suite; the full dashboard suite and changed-file lint pass.
