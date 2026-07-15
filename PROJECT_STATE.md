# VV Agent System — Project State

## Current checkpoint — 2026-07-15 (Technical Audit V1 backend complete)

The backend is one manual deterministic runtime. Scheduling, approval-resume,
legacy matcher/scorer/readiness/card generation, implementation handlers, and
legacy fallback behavior have been removed from the active Python application.
Frontend cutover remains deliberately deferred (the user's standing instruction).

All four deterministic technical-audit check sets are now implemented, tested,
and validated against the live BudgetYourMD site with a non-persisting smoke
run. No production baseline has been created and no production rows have been
written.

### Technical Audit V1 — implemented check sets

- **foundation:** llms.txt integrity, meta-title/description integrity, canonical
  integrity.
- **protocol:** robots.txt integrity/access (protego crawler registry),
  sitemap discovery/integrity/coverage/entry-health, TLS certificate/https
  redirect/mixed-content, JSON-LD schema integrity/coverage.
- **site_integrity:** internal/external link health, image integrity/alt-text,
  freshness dates, existing-source citation-link health.
- **performance:** CrUX p75 field metrics, three-run PageSpeed Insights
  Lighthouse median (external lab diagnostic), LCP lazy-load, GSC sitemap
  submission, Bing submission behavior.

Every check returns one of `pass | fail | review | unknown | not_applicable`
with evidence, applicability, scope, confidence, and a single next action. No
proprietary score, no matcher/similarity logic, and no LLM participates in the
technical path (guaranteed by a subprocess import test). Missing integration
API keys produce explicit `unknown`, never fabricated data.

### Finding lifecycle, grouping, and unified workflow

- Deterministic finding keys and run-over-run
  `new/continuing/changed/resolved/regressed` lifecycle classification.
- Identical-cause grouping (no similarity logic).
- Migration 018 adds `technical_audit_finding_groups`,
  `technical_audit_action_cards`, and `technical_audit_card_results` plus a
  `finding_key` column, all additive and RLS-protected. **Not yet applied to
  production.**
- Remediation catalogue emits platform-native Squarespace guided instructions
  (native SEO/domain/crawler settings; never edits generated sitemap XML,
  never fabricates file-editor access).
- Workflow state machine: `observed → draft_prepared → approved → applied →
  verified / still_failing`, with a stale-state guard that refuses to apply a
  draft whose audited precondition fingerprint no longer matches production, and
  deterministic re-audit verification that only marks `verified` when the exact
  originating checks pass on fresh evidence. No card publishes automatically.
- Authenticated FastAPI endpoints: `GET /api/technical-audit/runs`,
  `/runs/{id}`, `/cards`, and card `approve`/`reject`/`mark-applied`/`verify`
  (409 on illegal transitions, 404 on missing cards). Schedule/approval-resume
  endpoints still return 404.

### Validation evidence (2026-07-15)

- **Backend tests:** 354 passed (one pre-existing Starlette/httpx deprecation
  warning).
- **Live full-set smoke:** `cli smoke --domain budgetyourmd.ca --platform
  squarespace --check-sets foundation,protocol,site_integrity,performance`
  produced 216 results (132 pass, 3 fail, 36 review, 14 unknown, 31 N/A). The
  bare→www redirect was accepted, Squarespace `llms.txt` was Not Applicable, the
  TLS certificate passed, page-speed checks were Unknown (no CrUX/PSI keys in the
  smoke environment), and Bing was Unknown with an integration owner. Every
  result carried complete contract fields. No Supabase rows were written.
- **Production re-verified zero:** 1 client, 8 queries, 0 tracker/pipeline/
  improvement/technical-audit runs. Migration 018 tables are absent in
  production (not applied).

### Remaining gates before a production baseline

- **Local Supabase persistence validation is not run.** It requires Docker,
  which is not installed on the current machine, so the persisted demo run and
  local migration 001–018 apply could not be executed here. The persistence,
  lifecycle, grouping, and card-creation logic is covered by fake-Supabase unit
  tests. This live local run remains a gate before any production baseline.
- Migration 018 must be applied to production (schema only, empty tables) after
  review.
- Frontend cutover (Phase 8) is deferred per the standing instruction.

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
