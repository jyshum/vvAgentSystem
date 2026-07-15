# Technical Audit Backend-First Sequencing

**Status:** Approved in conversation on 2026-07-15.

## Objective

Finish and test the deterministic technical-audit backend before spending more time on dashboard configuration or legacy frontend removal.

## Immediate scope

- Keep migration 016 and its internal `site_platform` and `implementation_mode` fields.
- Keep the scheduler-free Python runtime.
- Revert the incomplete dashboard configuration change from Task 3.
- Build the manual evidence graph, technical-audit persistence, bounded Foundation collector, reset utility, and explicit audit CLI.
- Remove legacy Python matcher, scoring, card-generation, approval, and implementation runtime paths when their backend replacements are ready.
- Validate the backend with automated tests, a development database, and a non-persisting BudgetYourMD smoke run.

## Deferred scope

- Dashboard configuration for platform and implementation mode.
- Dashboard navigation, card, approval, page, schedule, and presentation cleanup.
- Migration 017 table/column deletion while the existing dashboard still reads legacy contracts.
- Production baseline creation.

## Data and deployment boundary

BudgetYourMD's platform remains an internal database value (`squarespace`); no frontend control is required for backend validation. Generated client data may be reset only after the reset utility and backend validation pass. Legacy tables remain present but empty until the frontend cutover is complete, preventing the current dashboard from breaking against missing relations.

## Success criteria

The backend tranche is complete when:

1. No automatic scheduler or approval/implementation path remains in the Python runtime.
2. A manual run can collect bounded evidence and persist deterministic Foundation results without matcher/scoring heuristics or action cards.
3. The reset utility proves dry-run export, client-scoped deletion, and preservation checks.
4. Automated backend tests pass.
5. A development persistence run and non-persisting BudgetYourMD smoke run pass.
6. Production still has no new baseline.

Frontend cutover and destructive schema cleanup require a separate plan after these criteria are met.
