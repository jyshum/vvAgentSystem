# Technical Audit v1 — Operator Guide

## Current rollout state

The technical-audit foundation is **development only** on branch `feature/deterministic-technical-audit`.

- The feature defaults off.
- Migration `014_technical_audit_foundation.sql` has not been applied to production by this branch.
- No result can create an action card, approve a change, or publish to a client website.
- This first slice checks `llms.txt`, meta titles, meta descriptions, and canonical declarations. The remaining approved sections are delivered through the follow-on plans listed in the foundation plan.

## Enable or disable

Set the agent environment variable:

```bash
TECHNICAL_AUDIT_V1_ENABLED=true
```

When true, a new improvement run uses the versioned checklist and skips the legacy structural scorer and its technical-card generator. Query matching, competitive gaps, content-gap cards, and community-check cards remain independent.

To use the rollback route:

```bash
TECHNICAL_AUDIT_V1_ENABLED=false
```

False is the default. It does not delete stored checklist runs; it only prevents new checklist invocation and preserves the legacy run path.

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
```

The migration is additive. It creates:

- `client_site_profiles`
- `technical_audit_runs`
- `technical_audit_observations`
- `technical_audit_results`

It does not drop or reinterpret `page_citation_scores`, `action_cards`, or historical improvement runs.

## Validate a development run

1. Apply migration 014 to the development/staging project.
2. Insert or update a `client_site_profiles` row for the test client.
3. Set `TECHNICAL_AUDIT_V1_ENABLED=true` in the agent environment.
4. Run an improvement cycle against a nonproduction test client/site.
5. Confirm one `technical_audit_runs` row links to the improvement run.
6. Confirm every result has applicability, scope, confidence, next action, and evidence references.
7. Confirm each evidence reference resolves to `technical_audit_observations.observation_ref` in the same run.
8. Confirm `page_citation_scores` receives no new row and no technical `action_cards` are created for the enabled run.
9. Open the run page and inspect the five status counts and section details.
10. Set the flag false and confirm the rollback route creates no new technical-audit run.

## Failure handling

- A check-level access problem becomes Unknown with a next action.
- A technical-audit runner exception marks only `technical_audit_runs.status=error`; the query/content pipeline may continue.
- A whole improvement-pipeline exception returns empty technical-audit state and follows the existing improvement error handling.
- Stored `llms.txt` evidence excludes the full body. It keeps a maximum 4,000-character excerpt, byte count, fingerprint, response metadata, and retrieval provenance.

## Verification commands

```bash
cd agents
.venv/bin/python -m pytest -q

cd ../dashboard
npm test
npx eslint lib/technical-audit-types.ts components/runs/TechnicalAuditChecklist.tsx __tests__/components/technical-audit-checklist.test.tsx app/admin/clients/'[id]'/runs/'[runId]'/page.tsx
npm run build
```

The repository-wide dashboard lint currently has a pre-existing error in `components/admin/TriggerRunButton.tsx`. Changed-file lint for this feature must remain clean until that unrelated baseline issue is repaired.

## Production gate

Production migration and rollout require separate approval after:

- fixture-site validation;
- a real development/staging run;
- evidence/status review by the founders;
- database backup/rollback confirmation;
- confirmation that the default-off flag is present in the production environment;
- approval of the next protocol-integrity tranche.
