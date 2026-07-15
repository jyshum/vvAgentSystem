# Technical Audit Frontend Deferral

**Status:** Approved in conversation on 2026-07-15.

## Objective

Finish and test the complete deterministic technical-audit revamp without spending time on dashboard configuration or frontend cleanup during this tranche.

## Immediate scope

- Keep migration 016 and its internal `site_platform` and `implementation_mode` fields.
- Keep the scheduler-free Python runtime.
- Revert the incomplete dashboard configuration change from Task 3.
- Build the manual evidence graph, technical-audit persistence, bounded Foundation collector, reset utility, and explicit audit CLI.
- Remove legacy Python matcher, scoring, card-generation, approval, and implementation runtime paths when their backend replacements are ready.
- Apply migration 017, including destructive legacy table/column cleanup, after the verified BudgetYourMD reset.
- Replace the Railway checkpoint store and deploy the scheduler-free runtime.
- Execute and verify the client-specific production reset while preserving configuration, queries, authentication, access, and credentials.
- Validate the backend with automated tests, a development database, and a non-persisting BudgetYourMD smoke run.

## Deferred scope

- Dashboard configuration for platform and implementation mode.
- Dashboard navigation, card, approval, page, schedule, and presentation cleanup.
- Production baseline creation.

## Data and deployment boundary

BudgetYourMD's platform remains an internal database value (`squarespace`); no frontend control is required for backend validation. Generated client data may be reset only after the reset utility and backend validation pass. Migration 017 still removes the approved legacy tables and columns in this tranche. Because frontend work is explicitly deferred and no one depends on the old interface, the existing dashboard may remain stale or broken against the cleaned schema until the later frontend cutover.

## Success criteria

The backend tranche is complete when:

1. No automatic scheduler or approval/implementation path remains in the Python runtime.
2. A manual run can collect bounded evidence and persist deterministic Foundation results without matcher/scoring heuristics or action cards.
3. The reset utility proves dry-run export, client-scoped deletion, and preservation checks.
4. Migration 017 removes the approved legacy schema after the successful reset.
5. The scheduler-free runtime and replacement checkpoint store are deployed and verified.
6. Automated backend tests pass.
7. A development persistence run and non-persisting BudgetYourMD smoke run pass.
8. Production still has no new baseline.

Only the frontend cutover is deferred to a separate plan.
