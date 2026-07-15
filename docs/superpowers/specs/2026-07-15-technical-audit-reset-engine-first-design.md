# Technical Audit Reset and Engine-First Delivery

**Status:** Approved

**Date:** 2026-07-15

**Scope:** Replace the compatibility-first rollout with one manual, deterministic runtime; reset BudgetYourMD generated data; finish and validate all four technical-audit check sets before building the unified action-card workflow.

**Builds on:**

- `2026-07-14-deterministic-technical-audit-design.md` for normative evidence and rule semantics;
- `2026-07-14-v1-simplification-technical-audit-expansion-design.md` for the four check sets and AI boundary.

This design supersedes their legacy-preservation, dual-route rollout, scheduling, and client-site-profile configuration decisions. It does not weaken the approved deterministic checks or remediation safety rules.

## Decisions

1. There is one active runtime, not parallel legacy and technical routes.
2. Runs are manual until scheduling is separately designed, approved, and explicitly enabled.
3. BudgetYourMD generated and historical data is reset before the new baseline.
4. Client configuration is one coherent user-facing object. Audit/check versions are generated internally per run.
5. Evidence collectors and all four check sets are completed and tested before unified workflow cards are built.
6. The first complete manual BudgetYourMD run becomes the only product baseline.
7. Matcher, similarity, structural scoring, readiness scoring, and heuristic technical-card code do not participate in the new runtime.

## Preserved State

The reset preserves only reusable inputs and access:

- the BudgetYourMD client identity, brand, domain, variations, and competitors;
- approved queries, paraphrases, buckets, statuses, and versions;
- Squarespace as the site platform and copy/paste or guided delivery as the implementation mode;
- the Google Search Console property and required environment credentials;
- Supabase authentication users, client access, administrator access, and roles;
- verified client facts that are explicitly confirmed in the future, not inferred generated output.

For the current live client, the normalized configuration is:

```yaml
client_name: Christian
brand_name: BudgetYourMD
domain: budgetyourmd.ca
site_platform: squarespace
implementation_mode: copy_paste
gsc_property: https://www.budgetyourmd.ca/
run_mode: manual
```

Brand variations, competitors, and the eight active versioned queries remain unchanged.

## Generated State Reset

The one-time reset exports a private, uncommitted snapshot and a row-count manifest before deletion. The snapshot is for operational recovery only and is never rendered in the product or used as the new baseline.

Generated rows to remove include:

- tracker runs and raw tracker results;
- prompt and visibility scores;
- competitive gaps;
- pipeline and improvement executions;
- page inventories, query-page matches, and readiness/citation scores;
- legacy and technical action cards plus implementation history;
- technical-audit runs, observations, and results;
- reports;
- Railway/LangGraph checkpoint and thread execution history.

The reset must be client-scoped where a client key exists. Child records without a direct client key are selected through their owning run. Deletion happens in foreign-key-safe order inside a transaction for Supabase data. After deletion, the reset verifies every generated table is empty for BudgetYourMD and verifies the preserved client, queries, GSC property, and access state exactly match the pre-reset manifest.

The first-tranche schema cleanup drops `page_inventory`, `query_page_matches`, `page_citation_scores`, and the legacy-shaped `action_cards` table after their rows are exported and deleted. The new evidence layer writes directly to bounded technical observations, and the later unified-card tranche creates a purpose-built workflow table linked to immutable results. Tracker, prompt-score, competitive-gap, pipeline/improvement-run, report, and technical-audit tables remain because the new runtime still uses them; their generated rows start empty.

The Railway checkpoint database is handled separately from the Supabase transaction. The deployed runtime is quiesced first. A new empty Postgres checkpoint store is provisioned and wired only to the agent service, emptiness and new checkpoint writes are verified, and the old checkpoint service is deleted after reset signoff. The agent is not restored for production manual runs until both Supabase and the replacement checkpoint store pass reset verification.

## Scheduling Removal

The current Railway service has no Railway cron. Recurrence is created in-process by APScheduler in `agents/server.py`. Therefore changing `cycle_frequency` alone does not provide a safe halt.

The active product removes:

- APScheduler startup and shutdown hooks;
- automatic job creation after a first run;
- schedule reload and schedule-list endpoints;
- schedule controls, next-run messaging, and automatic-schedule copy in the dashboard;
- `cycle_frequency` and `cycle_day` from the client configuration contract;
- the APScheduler dependency once no runtime code uses it.

The server remains available for authenticated manual runs. A future scheduler is a separate feature with an explicit enable/disable state; it is not inferred from a default weekday.

Scheduling removal is deployed before destructive data deletion so no automatic process can repopulate the cleared tables.

## Unified Client Configuration

Operators see one client configuration surface. Storage boundaries are internal and must not create additional setup concepts.

User-managed fields are limited to:

- client and brand identity;
- production domain;
- site platform;
- implementation mode or connected implementation integration;
- brand variations and competitors;
- Search Console property/integration;
- approved queries;
- access and roles.

Users do not configure:

- audit version or check version;
- check sets;
- `llms.txt` applicability;
- priority URLs;
- empty integration-state or verified-facts placeholders;
- schedule fields while the product is manual-only.

The engine derives Squarespace `llms.txt` absence as Not Applicable. Audit and check versions are selected by code and persisted on runs/results for reproducibility. Integration applicability is derived from real connection state. Platform limitations affect implementation mode, never observed audit truth.

The existing `client_site_profiles` table is removed during the first tranche so it cannot remain a second, hidden configuration model. Platform and implementation mode become columns in the unified client contract. Run provenance belongs only to run and result records.

## One Runtime

An explicit manual run performs independent product tracks:

```text
approved query inputs
        |
        +--> AI visibility collection --> tracker evidence
        |
        +--> bounded site evidence --> deterministic check registry
                                   --> immutable observations/results
        |
        +--> bounded community selection from measured competitor leads
```

The runtime does not call or fall back to:

- query-page embedding matching;
- matched, weak, or content-gap classification;
- structural/citation-readiness scoring;
- legacy crawlability heuristics;
- AI-generated technical fixes based on those heuristics.

Technical failure does not fabricate results or invoke legacy behavior. It records an Error or check-level Unknown with a precise retry/unblock action. Visibility and community tracks may retain their own independent success/failure boundaries.

## Engine-First Delivery

Implementation is divided into bounded plans rather than one combined rewrite.

### Tranche 0: reset, manual runtime, configuration, and Foundation validation

1. Remove scheduling and automatic recurrence.
2. Add and verify the one-time private export/reset operation.
3. Reset BudgetYourMD generated Supabase and Railway checkpoint data.
4. Remove the dual legacy/technical route and legacy heuristic calls from the active runtime.
5. Normalize the user-facing client configuration.
6. Repair the shared HTTP/inventory layer, including bare-domain to `www` redirect handling, canonical host equivalence, provenance, limits, and safe failures.
7. Remove user-configured priority URL and `llms.txt` controls from Foundation. Missing descriptions on audited canonical indexable HTML pages become Review, never Fail; pages outside the bounded audit sample produce no result. Squarespace `llms.txt` absence is derived as Not Applicable.
8. Validate Foundation with deterministic fixtures, non-persisting BudgetYourMD smoke checks, and a staging execution.

This tranche does not create the production baseline.

### Tranche 1: Protocol

Implement and validate standards-based robots, sitemap, TLS/HTTPS, and schema integrity/coverage collectors and checks. Each check stores bounded evidence and supports Pass, Fail, Review, Unknown, and Not Applicable without hidden scores.

### Tranche 2: Site integrity

Implement and validate bounded broken-link, image, freshness, and existing-source-support collectors and checks. Semantic AI assistance remains constrained to Review-class work over retrieved evidence.

### Tranche 3: Performance and connected services

Implement and validate CrUX field evidence, controlled Lighthouse diagnostics, Google Search Console, and Bing checks. Disconnected or insufficient integrations become explicit Unknown or Not Applicable according to declared scope.

### Tranche 4: unified cards and Squarespace workflow

Compose immutable results and editable workflow state into one founder-readable card. Add grouping, lifecycle, stale-state protection, guided Squarespace instructions, approval, application state, and fresh re-audit verification. No card may publish automatically.

### Baseline gate

Only after all four check sets and the result UI pass staging validation is one authenticated manual BudgetYourMD run persisted as the baseline. It reruns the approved queries, measures visibility from empty generated tables, executes the complete deterministic audit, and creates only the new workflow objects. All future comparisons start from that run.

## Evidence and Decision Contract

The approved five-state contract remains unchanged:

1. determine applicability;
2. return Not Applicable when the rule does not apply;
3. return Unknown when an applicable dependency cannot provide sufficient evidence;
4. return Pass when deterministic evidence meets the rule;
5. return Fail when deterministic evidence confirms a supported defect;
6. return Review when bounded context or judgment is required.

Every result includes its subject, expected condition, observed evidence, evidence references, applicability reason, scope, confidence, next action, check version, and retrieval provenance. There is no proprietary total technical score.

## Error Handling and Safety

- The deployed scheduler is removed before the reset begins.
- The reset aborts if preserved configuration cannot be exported or verified.
- Supabase deletion is transactional and rolls back on any failed statement or postcondition.
- Railway checkpoint cleanup is independently verified before runtime reactivation.
- Collector failures are explicit Unknowns or a run Error; they never become Pass.
- Count, byte, time, redirect, host, and concurrency limits are recorded in scope.
- Retrieval rejects unsafe private-network and credential-bearing targets.
- No AI output changes a deterministic status.
- No audit result directly mutates a production website.

## Testing and Promotion

Each tranche requires:

- unit fixtures for every supported status;
- parser and check-contract tests;
- mocked network/browser/API integration tests;
- blocked, redirected, malformed, ambiguous, oversized, and truncated cases;
- Squarespace-specific redirect, generated-sitemap, canonical, and unsupported-root-file cases;
- bounded end-to-end fixture execution;
- repeatability across reruns;
- evidence-to-result persistence verification;
- founder-readable frontend verification for delivered UI;
- a non-persisting BudgetYourMD production-site smoke check;
- a staging database run before any production baseline.

Production data remains empty after the reset until the baseline gate is explicitly reached. Merging or deploying code does not authorize a baseline run, re-enable scheduling, or publish a remediation.

## Acceptance Criteria

1. No recurring job exists in the deployed application or Railway configuration.
2. BudgetYourMD generated Supabase and checkpoint data is empty after a verified reset.
3. Brand, domain, competitors, GSC configuration, queries, credentials, authentication, and access remain intact.
4. Only one manual runtime path exists; no legacy heuristic fallback can execute.
5. Client configuration contains no user-facing audit/check version, priority URL, or schedule controls.
6. The four check sets produce versioned, evidence-backed five-state results.
7. The same observations and check versions always produce the same deterministic statuses.
8. No matcher, similarity, readiness score, or structural score influences technical results or cards.
9. BudgetYourMD's bare-domain redirect and `www` canonical are handled as valid production-domain evidence.
10. The complete staging audit is reviewed before a production baseline is authorized.
11. The first persisted post-reset run is the complete BudgetYourMD baseline.
12. Scheduling remains absent until separately designed and explicitly approved.
