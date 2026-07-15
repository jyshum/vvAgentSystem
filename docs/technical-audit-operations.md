# Technical Audit v1 — Operator Guide

## Current production state

The backend is manual-only and deterministic. Production scheduling and the
legacy matcher/scorer/readiness/card/implementation runtime are removed.
Migrations 014–017 are applied. The frontend cutover is deferred and may still
contain views for schema removed by migration 017.

BudgetYourMD has been reset to configuration-only state:

- 1 client: `03cfae03-7d1d-484f-94aa-f1e576ed299a`;
- domain `budgetyourmd.ca`;
- platform `squarespace`;
- implementation mode `copy_paste`;
- 8 active intent rows and 47 unique approved wordings;
- 2 unchanged authentication users;
- zero tracker, pipeline, improvement, report, or technical-audit runs.

No production baseline has been created. Development/staging validation is the
next gate and is currently paused.

## Runtime boundary

The active graph is:

```text
load_config -> run_tracker -> run_gsc -> run_technical_pipeline -> end
```

- `full`: visibility, GSC, then deterministic technical evidence.
- `tracker_only`: visibility and GSC, then end.
- `technical_only`: deterministic technical evidence without tracker/GSC.

The runtime does not call query-page matching, proprietary structural or
citation-readiness scores, content-gap classification, legacy crawlability
heuristics, action-card generation, approval resume, or implementation handlers.
A technical failure records an error or check-level Unknown and never falls back
to those deleted paths.

## Client configuration

The backend configuration contract is stored on `clients` and `queries`.
Operators configure identity, domain, platform, implementation mode, brand
variations, competitors, GSC property, approved intent rows/paraphrases, and
access. Operators do not configure audit versions, check versions, check sets,
priority URLs, `llms.txt` applicability, or schedules.

`client_site_profiles` no longer exists. Applicability is derived by code from
platform and collected evidence. Squarespace `llms.txt` absence is Not
Applicable.

### Query accounting

An intent is one `queries` row. Each row contains one canonical prompt plus its
approved paraphrases. BudgetYourMD currently has:

- 8 active intents;
- 47 unique wordings;
- 4 configured engines;
- 188 expected model requests per baseline at one run per wording.

Do not describe this as “8 queries.” Use “8 intents / 47 wordings.”

## Check sets

All four deterministic check sets are implemented and tested:

- **foundation:** `llms_txt.integrity`, meta-title/description integrity,
  canonical integrity.
- **protocol:** `robots_txt.integrity`/`.access`, `sitemap.discovery`/
  `.integrity`/`.coverage`/`.entry_health`, `tls.certificate`/
  `.https_redirect`/`.mixed_content`, `schema.integrity`/`.coverage`.
- **site_integrity:** `links.internal_health`/`.external_health`,
  `images.integrity`/`.alt_text`, `freshness.dates`,
  `source_support.link_health`.
- **performance:** `performance.crux`/`.lighthouse`/`.lcp_image`,
  `integration.gsc_sitemap`, `integration.bing`.

The collector is bounded by page, redirect, response-size, timeout, external-
probe (50), and image-probe (40) limits. It records request URL, redirect chain,
final URL, status, MIME type, retrieval time, fingerprint, truncation, and safe
error details, plus robots.txt, sitemap documents, TLS certificate facts, a
plain-HTTP probe, and bounded external/image probes. Bare and `www` production
hosts are treated as one approved site identity after observed redirection.

Performance API keys drive real calls only when present: `CRUX_API_KEY`,
`PAGESPEED_API_KEY`, and `BING_WEBMASTER_API_KEY`. Absent keys produce explicit
`unknown` results, never fabricated data. No LLM participates in the technical
path.

### Finding lifecycle and unified workflow

Persisted runs classify each finding as `new`, `continuing`, `changed`,
`resolved`, or `regressed` against the previous completed run, group
identical-cause findings, and create unified action cards over immutable
results. Cards follow `observed → draft_prepared → approved → applied →
verified/still_failing`, with a stale-state guard on apply and deterministic
re-audit verification. No card publishes automatically. Migration 018 adds the
workflow tables; it is not yet applied to production.

## Status handling

| Status | Meaning | Operator response |
|---|---|---|
| Pass | The applicable deterministic condition was observed and met. | No action. |
| Fail | A supported structural defect was confirmed. | Review evidence and the precise remediation. |
| Review | Context or bounded judgment is required. | Answer the named review question; do not label it a confirmed defect. |
| Unknown | An applicable check could not complete. | Follow the retry/unblock action; never present it as passing. |
| Not applicable | The rule does not apply to this platform/evidence. | No action unless the platform or scope changed. |

Missing descriptions on audited canonical indexable HTML pages are Review,
never Fail. Pages outside the bounded audit sample produce no result.

## Manual endpoints and CLI

The Railway service exposes:

- `GET /health`;
- authenticated `POST /api/run`;
- authenticated `GET /api/status/{thread_id}`;
- authenticated `POST /api/run-all`;
- authenticated `GET /api/technical-audit/runs?client_id=`;
- authenticated `GET /api/technical-audit/runs/{run_id}`;
- authenticated `GET /api/technical-audit/cards?client_id=&status=`;
- authenticated `POST /api/technical-audit/cards/{card_id}/approve`
  (body `{"approved_by": "<name>"}`), `/reject`, `/mark-applied`, `/verify`.

Card endpoints return 409 for an illegal state transition and 404 for a missing
card. Schedule and approval-resume endpoints must return 404.

The explicit audit CLI supports:

```bash
cd agents

# Non-persisting website smoke artifact (defaults to all four check sets)
.venv/bin/python -m src.technical_audit.cli smoke \
  --domain example.com \
  --platform other \
  --check-sets foundation,protocol,site_integrity,performance \
  --output ../.artifacts/technical-audit/example-smoke.json

# Persisted run: use only against an approved development/staging database
.venv/bin/python -m src.technical_audit.cli run --client-id <demo-client-uuid>
```

Do not run the persisted command against BudgetYourMD production until a new
baseline is explicitly authorized.

## Verified reset record

The ignored reset directory is:

```text
.artifacts/client-resets/budgetyourmd-2026-07-15/
```

It contains redacted table snapshots, safe auth projections, SHA-256 file
hashes, a reviewed manifest, an execute snapshot, and final verification.
Credentials and secret-shaped values are not serialized.

Pre-reset generated counts were:

| Table | Rows |
|---|---:|
| tracker_runs | 2 |
| tracker_results | 346 |
| prompt_scores | 59 |
| competitive_gaps | 16 |
| improvement_runs | 3 |
| page_inventory | 60 |
| query_page_matches | 24 |
| page_citation_scores | 4 |
| action_cards | 8 |
| pipeline_runs | 3 |
| reports | 0 |
| technical_audit_runs/results/observations | 0 |

The transaction required reviewed pre-counts and database-side fingerprints,
deleted only client-owned generated parents in foreign-key-safe order, verified
all generated counts were zero, and verified preserved fingerprints remained
unchanged before commit.

Migration 017 then removed legacy tables/columns. Final verification confirmed:

- 1 BudgetYourMD client;
- 8 unchanged intent rows / 47 unique wordings;
- 2 unchanged complete auth rows;
- zero generated rows;
- no legacy profile, page-match, readiness-score, inventory, or action-card
  tables;
- no production baseline.

## Railway checkpoint state

`vv-tracker` uses `${{checkpoints-v2.DATABASE_URL}}`. The replacement database
passed a direct checkpoint write/read/delete canary. The old Postgres service is
deleted. Railway cron is null, runtime logs contain no scheduler startup, health
returns 200, and `/api/schedules` returns 404.

## Next validation gate — not yet run

When explicitly approved, follow Task 12 in the tranche plan:

1. start/reset local Supabase and apply migrations 001–017;
2. seed the fixed demo client and query;
3. run targeted backend/dashboard verification;
4. persist one demo Foundation audit only to local Supabase;
5. run a non-persisting BudgetYourMD website smoke audit;
6. prove production counts remain zero.

Stop if any step would point the persisted CLI at production. Do not begin the
Protocol check set or a production baseline until the validation evidence is
reviewed.

## Failure handling

- Check-level access problems become Unknown with an owner and unblock action.
- Whole-run collection/persistence failure records Error and exits nonzero.
- Stored `llms.txt` evidence is bounded; full bodies are not persisted.
- No audit result can publish or mutate a client website.
- No legacy heuristic fallback exists.
