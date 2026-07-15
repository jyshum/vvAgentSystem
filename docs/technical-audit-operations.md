# Technical Audit v1 — Operator Guide

## Current rollout state

The technical-audit foundation is **development only** and is protected by a global flag, client allowlist, and check-set configuration.

- The feature defaults off.
- Migrations `014_technical_audit_foundation.sql` and `015_improvement_run_mode.sql` have not been applied to production.
- No technical audit result can approve a change or publish to a client website.
- The only implemented check set is `foundation`: `llms.txt`, meta titles, meta descriptions, and canonical declarations.
- Technical result/action composition and technical remediation cards are the next plan; this tranche creates only bounded manual community cards.

## Enable or disable

Set all rollout controls in the agent environment:

```bash
TECHNICAL_AUDIT_V1_ENABLED=true
TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS=demo-client-id-1,demo-client-id-2
TECHNICAL_AUDIT_CHECK_SETS=foundation
```

- A false or missing global flag uses the legacy route.
- A true flag with an empty allowlist enables no clients.
- A true flag with listed IDs enables V1 only for those clients.
- `*` enables all clients and is for development/testing only.
- For an active V1 client (global flag enabled and client allowlisted), an unavailable or empty `TECHNICAL_AUDIT_CHECK_SETS` fails closed before work; it is never a silent partial audit.
- When the global flag is disabled or a client is not allowlisted, check-set validation does not block that client and the legacy route continues unchanged.
- A technical-audit runtime error is reported by the V1 run and does not fall back to legacy heuristic content work.

Removing a client ID from the allowlist rolls that client back to the legacy route on its next run. Setting the global flag false rolls every client back to the legacy route:

```bash
TECHNICAL_AUDIT_V1_ENABLED=false
```

Neither rollback option deletes stored V1 evidence or results.

## V1 run boundary and preserved legacy views

For an allowlisted V1 client, the improvement pipeline bypasses legacy query matching, structural scoring, briefs, and AI fixes. It writes technical observations/results for `foundation` and directly selects at most five manual `community_check` cards from positive tracker competitor leads. It does not write `query_page_matches` or `page_citation_scores`, and it does not create technical remediation cards in this tranche.

The Pages primary tab is hidden, but the direct Pages route remains available for legacy data. Run pages use the immutable `improvement_runs.run_mode` value, not the existence of a `technical_audit_runs` child, to select their presentation. A `technical_v1` run therefore remains technical when audit initialization fails before a child row is created. Historical rows default to `legacy` and preserve their legacy badge, matching evidence, and readiness evidence even if an older technical-audit child exists.

## Status handling

| Status | Meaning | Operator response |
|---|---|---|
| Pass | The applicable deterministic condition was observed and met. | No action. Evidence remains inspectable. |
| Fail | A supported structural defect was confirmed. | Read evidence and next action. A later remediation workflow may stage a fix; v1 does not create one. |
| Review | The condition is contextual or needs bounded judgment. | Review the named question/evidence; do not treat it as a defect automatically. |
| Unknown | An applicable check could not complete. | Follow the stated unblock/retry action. Never present it as passing. |
| Not applicable | The rule does not apply under the current profile/page evidence. | No action. Verify the applicability reason if the profile changed. |

## Client profile controls

`client_site_profiles` stores one reusable profile per client.

- `llms_txt_enabled=false`: an absent root file is Not applicable. An unexpected existing file is Review.
- `llms_txt_enabled=true`: the root file is expected, so missing/empty/HTML fallback content can fail.
- `priority_urls`: missing meta descriptions on these URLs become Review. Missing descriptions on nonpriority pages are Not applicable in this slice.
- `platform`: records the implementation platform without changing audit truth.
- `verified_facts` and `integration_state`: reserved for approved factual context and connected-service state in subsequent sections.

The profile changes applicability; it does not override observed HTTP/HTML evidence.

## Development database setup

Use a development or staging Supabase project. Do not test this migration first against the live client database.

Apply:

```text
supabase/migrations/014_technical_audit_foundation.sql
supabase/migrations/015_improvement_run_mode.sql
```

Apply them in numeric order. Migration 014 creates:

- `client_site_profiles`
- `technical_audit_runs`
- `technical_audit_observations`
- `technical_audit_results`

Migration 015 additively extends `improvement_runs` with:

- `run_mode`, constrained to `legacy` or `technical_v1`;
- `effective_check_sets`, a non-null `text[]` containing the check sets selected at insertion;
- a trigger preventing either route field from being changed after insertion.

Existing rows receive the safe defaults `run_mode='legacy'` and `effective_check_sets='{}'`. The migration does not inspect `technical_audit_runs`, so an older child row cannot reclassify or reinterpret a historical run. New pipeline inserts explicitly persist `technical_v1` plus `foundation` for active V1, or `legacy` plus an empty set for disabled/nonallowlisted clients. Neither migration drops or reinterprets `page_citation_scores`, `query_page_matches`, `action_cards`, or historical improvement evidence.

## Next operator validation gate: validate a development/staging run

This manual fixture validation has not been run as part of this documentation tranche. On a development/staging Supabase project only:

1. Enable one demo client by ID with `foundation`.
2. Run the improvement pipeline with at least seven positive tracker competitor leads.
3. Confirm the run writes technical observations/results and at most five `community_check` cards.
4. Confirm it writes no `query_page_matches` or `page_citation_scores` rows.
5. Confirm the query page has no PAGE, similarity, or WEAK column.
6. Confirm the run page uses its persisted `technical_v1` marker and has no matching, content-gap, or readiness-score claims.
7. Simulate audit initialization failure before child insertion and confirm the marked run stays technical with neutral unavailable/error guidance.
8. Open an older legacy run URL, including a fixture with an older technical-audit child, and confirm the legacy badge, matching evidence, readiness evidence, and direct Pages route still render.
9. Remove the client ID from the allowlist and confirm the next run is inserted as `legacy` with no effective check sets.

## Failure handling

- A check-level access problem becomes Unknown with a next action.
- A technical-audit runtime error is reported by the V1 run and does not invoke legacy heuristic content work as a fallback.
- A whole improvement-pipeline exception follows the existing improvement error handling.
- Stored `llms.txt` evidence excludes the full body. It keeps a maximum 4,000-character excerpt, byte count, fingerprint, response metadata, and retrieval provenance.

## Verification commands

```bash
cd agents
.venv/bin/python -m pytest -q

cd ../dashboard
npm test
npm run build
npx eslint \
  lib/client-tabs.ts \
  lib/improvement-types.ts \
  lib/run-presentation.ts \
  components/admin/HeatTable.tsx \
  app/admin/clients/'[id]'/layout.tsx \
  app/admin/clients/'[id]'/queries/page.tsx \
  app/admin/clients/'[id]'/runs/'[runId]'/page.tsx \
  __tests__/client-tabs.test.ts \
  __tests__/run-presentation.test.ts \
  __tests__/components/heat-table.test.tsx
```

The repository-wide dashboard lint still has a pre-existing error in `components/admin/TriggerRunButton.tsx` (`react-hooks/set-state-in-effect`); it also reports warnings in that file and `app/layout.tsx`. Changed-file lint for this feature must remain clean until the unrelated baseline issue is repaired.

## Production gate

Production migration and rollout require separate approval after:

- fixture-site validation;
- a real development/staging run;
- evidence/status review by the founders;
- database backup/rollback confirmation;
- confirmation that the default-off global flag, empty allowlist, and `foundation` check-set configuration are present in the production environment;
- approval of the next protocol-integrity tranche.
