# VV Agent System — Project State

## Current checkpoint — 2026-07-15

The backend is now one manual deterministic runtime. Scheduling, approval-resume,
legacy matcher/scorer/readiness/card generation, implementation handlers, and
legacy fallback behavior have been removed from the active Python application.
Frontend cutover remains deliberately deferred.

### Production infrastructure

- **Supabase:** `vv-dashboard` is live in US West.
- **Railway app:** `vv-tracker` is deployed and healthy with no cron or in-process
  scheduler. `/health` returns 200 and `/api/schedules` returns 404.
- **Railway checkpoints:** `checkpoints-v2` is the only checkpoint database. It
  passed a real write/read/delete canary; the old Postgres service was deleted.
- **Dashboard:** the existing frontend remains deployed but was not adapted to
  migration 017. Routes that depend on removed legacy tables or columns may be
  stale until the separate frontend cutover.

### Supabase schema and reset

- Migrations 014 and 015 were previously applied.
- Migration 016 added `clients.site_platform` and
  `clients.implementation_mode`.
- Migration 017 removed legacy runtime tables and columns, including
  `client_site_profiles`, page matching/readiness/card tables, scheduling fields,
  legacy CMS fields, and obsolete improvement-run routing/statistics.
- MCP migration records:
  - `20260715095531_unified_manual_client_config`
  - `20260715100006_remove_legacy_runtime`
- The verified BudgetYourMD reset backup is local and Git-ignored at
  `.artifacts/client-resets/budgetyourmd-2026-07-15/`.

### BudgetYourMD preserved state

- Client ID: `03cfae03-7d1d-484f-94aa-f1e576ed299a`
- Domain: `budgetyourmd.ca`
- Platform: `squarespace`
- Implementation mode: `copy_paste`
- Query model: 8 active intent rows containing 47 unique approved wordings.
- A future visibility baseline would make 188 model requests at one run per
  wording across ChatGPT, Perplexity, Claude, and Gemini.
- Authentication: 2 complete `auth.users` rows were fingerprinted before and
  after reset and remained unchanged.
- `client_users`: 0 rows existed before reset and 0 remain; current administrator
  access is therefore not represented by a client-specific mapping row.
- Generated state: tracker, tracker-result, prompt-score, competitive-gap,
  pipeline, improvement, report, and technical-audit counts are all zero.
- No production baseline or production technical-audit result has been created.

## Active deterministic audit slice

Only the `foundation` check set is implemented:

- `llms.txt` integrity with platform-derived applicability;
- meta-title integrity;
- meta-description integrity;
- canonical integrity.

The collector is bounded, records retrieval provenance, accepts the approved
bare/`www` production-host pair, and fails safely. Squarespace `llms.txt`
absence is Not Applicable. Missing descriptions on audited canonical indexable
HTML pages are Review, never Fail.

The manual graph is:

```text
load_config -> run_tracker -> run_gsc -> run_technical_pipeline -> end
```

`technical_only` skips tracker/GSC. `tracker_only` ends after GSC. Technical
failures never call removed legacy heuristics or fabricate results.

## Verification evidence

- Backend: 251 tests passed; one pre-existing Starlette/httpx deprecation
  warning.
- Dashboard: 108 tests passed and the Next.js production build succeeded before
  the schema reset. This does not mean the deferred frontend is compatible with
  migration 017.
- Reset: reviewed pre-counts and preserved SHA-256 fingerprints were enforced
  inside the deletion transaction; post-delete counts were zero and preserved
  fingerprints were unchanged.
- Final production verification confirmed 1 client, 8 intents, 47 unique
  wordings, 2 unchanged auth users, zero generated rows, and all approved legacy
  tables/columns absent.

## Paused next gate

Development/staging validation has **not** been run. Do not start a production
baseline. The next approved work, only after explicit instruction, is Task 12
in `docs/superpowers/plans/2026-07-15-technical-audit-tranche-0.md`:

1. migrate local Supabase;
2. seed a fixed demo client;
3. run targeted automated tests;
4. persist one demo Foundation audit locally;
5. run a non-persisting BudgetYourMD website smoke audit;
6. re-verify production remains empty.

Do not plan or implement Protocol checks until that evidence is reviewed.

## Key documents

- Normative design:
  `docs/superpowers/specs/2026-07-14-deterministic-technical-audit-design.md`
- Reset/runtime design:
  `docs/superpowers/specs/2026-07-15-technical-audit-reset-engine-first-design.md`
- Tranche plan:
  `docs/superpowers/plans/2026-07-15-technical-audit-tranche-0.md`
- Operator guide: `docs/technical-audit-operations.md`
