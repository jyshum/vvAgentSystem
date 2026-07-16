# Technical Audit Frontend Cutover

**Status:** Approved in conversation on 2026-07-16.

## Context

The deterministic technical audit backend is complete (357 tests passing, migration 018 applied to production). The frontend was deliberately deferred by the 2026-07-15 backend-first tranche and is now the only work between here and a production baseline.

Today the audit has no home of its own. `TechnicalAuditChecklist.tsx` renders inside the run-detail page, gated behind an improvement run existing, below the funnel tiles. Meanwhile the frontend still carries screens built for the deleted matcher/scorer/auto-approve engine (commit `375906c`), which display `/100` scores computed from a formula copied out of `agents/src/improvement/scorer.py` — a file that no longer exists.

This cutover gives the audit a dedicated admin surface, exposes the finding-group and lifecycle engines that the backend already computes but nothing displays, and removes the contradictory legacy screens.

## Decisions

| Decision | Choice |
|---|---|
| Audience | Admin only. Client-facing RLS in 018 stays dormant. |
| Structure | One `AUDIT` tab; cards live inside it. `CARDS` tab retired. |
| Card content | Gap (NOW / EXPECTED) plus observed facts. Instructions collapsed. |
| Draft text | **None in V1.** No generated fixes. |
| Audit trigger | Standalone `Run audit` — requires a new backend endpoint. |
| RUNS tab | Untouched. Revisited as separate work after AUDIT ships. |
| Legacy screens | Delete `CARDS` tab and `/pages` route. `/admin/approvals` deferred — see below. |

### On the absence of drafted content

Cards show what is missing, never a proposed fix. This is a deliberate reversal of the old `card_generator.py` → `card_qa.py` → `scorer.py` → `auto_approve.py` chain, whose core defect was drafting content ungrounded in what the page actually said — unacceptable for a medical client.

The new architecture already eliminates that chain's other three defects by construction: no auto-apply, no score, and a deterministic re-fetch as verifier rather than a second LLM. Generation is the only one left, and V1 declines it.

This remains additive later. `technical_audit_action_cards.copy_values` (jsonb) is the natural home for a draft field; adding one needs no migration. If a drafter is ever built it must be **extractive** — permitted only to select and compress content already on the page, never to introduce a claim — and must display its source passage alongside the draft.

## Architecture

### Data flow: reads and writes take different paths

**Reads — direct Supabase from Server Components.** `createAdminClient()` (`lib/supabase/admin.ts`) queries `technical_audit_runs`, `technical_audit_results`, `technical_audit_finding_groups`, `technical_audit_action_cards`. This is the dominant pattern across every existing admin page.

**Writes — Next route handler → FastAPI.** Card transitions and the run trigger proxy to FastAPI, following `app/api/runs/trigger/route.ts` exactly: `getUser()` → admin check → 503 if `LANGGRAPH_API_URL`/`LANGGRAPH_API_KEY` unset → `Authorization: Bearer` → 502 on upstream failure.

**Why writes must not take the short path.** A direct `UPDATE ... SET status='applied'` would be fewer lines, and both the service-role client and RLS would permit it. It would also be a correctness bug. Every transition in `workflow.py` carries logic invisible to the UI: `mark_applied` re-fetches the live site and refuses when the audited fingerprint no longer matches (the stale-precondition guard); `verify` re-collects the full site and re-runs the checks. A direct table write sets a field and silently skips all of it, producing cards marked `verified` that nobody verified. **The state machine is the only door.**

### Backend addition

`POST /api/technical-audit/runs` in `agents/server.py` — starts a standalone audit with `improvement_run_id=None`, on a background thread, mirroring `/api/run`.

`improvement_run_id` is already nullable (`014_technical_audit_foundation.sql:20`) and `_run_and_persist_technical_audit()` already takes it as a parameter, so this is a decoupling, not a rework: extract the audit body out of `run_technical_pipeline()` in `pipeline.py` so the pipeline node and the new endpoint share one implementation.

### Frontend components

`app/admin/clients/[id]/audit/page.tsx` — RSC composing:

- `AuditSummary` — status counts, run switcher, `Run audit` (client)
- `LifecycleStrip` — regressed / new / resolved / changed since previous run
- `ActionCard` — one per finding group: title, status + lifecycle chips, affected subjects, NOW/EXPECTED, observed facts, collapsed instructions, collapsed evidence
- `CardActions` (client) — buttons rendered from `card.status`
- `FindingsSections` — the existing `TechnicalAuditChecklist` accordion, moved not rebuilt

Supporting: `app/api/technical-audit/**/route.ts` proxies; `lib/technical-audit-types.ts` extended with card/group types and `severity` dropped (frontend-only — it remains on the backend `CheckResult` model); `lib/client-tabs.ts` gains `AUDIT`, loses `CARDS`.

### Presentation rules

- **Group by cause, not page.** One card per `finding_group`, listing affected subjects. Never N near-identical rows.
- **Lifecycle strip leads**, `regressed` first and in `--neg`. It is the only signal in the product that reports a past fix breaking again.
- **No scores anywhere.**
- Existing house style: CSS-variable inline colors, mono micro-labels at `text-[8px] uppercase tracking-[0.12em]`, `font-display` numerals, hairline grid. No shadcn (the app has none).

### Design constraints (Redesign - Preserve)

Mode is **preserve**, not overhaul. The existing design language is deliberate and coherent; the AUDIT tab joins it rather than reinterpreting it. New components are indistinguishable in style from `TechnicalAuditChecklist.tsx` and `app/admin/approvals/page.tsx`.

Extracted tokens, all already defined in `app/globals.css` - **use these, add none**:

| Role | Token |
|---|---|
| Surfaces | `--ink` `#0e0e0f`, `--ink-soft` `#141416`, `--ink-2` `#19191c` |
| Text | `--white`, `--mute` (58%), `--faint` (36%) |
| Lines | `--hair` (11%), `--ghost` (13%) |
| Status | `--pos` `#84d8ab`, `--neg` `#e89aa0`, review `#d4a017` |
| Type | `font-display` Cormorant Garamond, `font-serif` Newsreader, `font-mono` IBM Plex Mono |

House idioms to follow: colors applied as CSS-variable **inline styles**, not utility classes; mono micro-labels at `text-[8px] uppercase tracking-[0.12em]` in `--faint`; numerals in `font-display font-light`; the `gap-px` + `background: var(--hair)` hairline-grid trick for tiles; sharp corners (radius 0) throughout.

Hard constraints:

- **No new dependencies.** The app has no shadcn, no Radix, no CVA, no icon library, no Motion. Do not introduce one. Existing `components/ui/` primitives (`Badge`, `Card`, `Button`) are hardcoded to tracker variants and are **not** extensible to audit statuses - follow `TechnicalAuditChecklist`'s precedent of local status chips rather than widening `Badge`.
- **Dark only.** The app is single-theme; `--*-paper` tokens exist solely for the cream report document. No `prefers-color-scheme` handling.
- **Static.** Motion is effectively absent from this codebase. Do not add animation.
- **No em-dashes in any user-visible string.** Use a hyphen or restructure.
- **No decorative status dots, no fake-precise numbers, no invented names.** All displayed values come from real audit rows.
- **Contrast:** status colors must clear WCAG AA against `--ink`/`--ink-soft`.

The general-purpose taste skill (`design-taste-frontend`) is **out of scope by its own Section 13** (dashboards / dense product UI / admin panels / data tables) and its defaults conflict directly with this codebase - it discourages the mono micro-labels and serif display face that define this house style, and requires an icon library the project does not have. Only its Section 11 redesign-preserve protocol applies, and it is discharged by the table above.

### Error handling

The five states already model uncertainty, so the UI never manufactures certainty: `unknown` renders as unknown rather than failure; absent API keys render "not configured"; `running`/`error` runs keep the existing treatment. Two paths need real UI:

- **409 stale precondition** on mark-applied — surface the refusal and offer a re-audit. This is the guard working, not a fault.
- **503 unconfigured** — disable `Run audit` with a stated reason.

## Deletions

Both targets below were verified to have **no inbound links** other than their own definitions:

- `app/admin/clients/[id]/cards/` — reads the frozen `action_cards` table; referenced only by `lib/client-tabs.ts`, which loses the entry.
- `app/admin/clients/[id]/pages/` and `components/pages-tab/` — unreachable by navigation (absent from `clientTabs()`); `PagesTable.tsx` hardcodes scoring weights citing the deleted `agents/src/improvement/scorer.py`.

Plus their tests.

### `/admin/approvals` is NOT deleted

Initially scoped for removal, then rejected on inspection. It is part of the same dead system — it reads `action_cards`, which no backend writes — but it is **not orphaned**:

- it is a top-level nav item (`components/admin/NavLinks.tsx:9`)
- it is deep-linked from `components/board/BoardRow.tsx`, `components/admin/HeatTable.tsx`, `lib/run-presentation.ts:60`, and the run-detail page (`runs/[runId]/page.tsx:424`)

Removing it means editing the board, the heat table, and `run-presentation.ts` — surfaces this cutover deliberately does not touch. It is a coherent follow-up on its own, alongside the RUNS redesign, and should not be smuggled into this one.

RUNS internals (MATCHING / LEGACY READINESS tiles, the `run-presentation.ts` legacy branch) likewise stay out of scope.

## Testing

Component tests in `__tests__/components/` alongside the existing `technical-audit-checklist.test.tsx`:

- lifecycle strip renders correct counts per state
- cards group by cause; a 4-subject group renders one card
- buttons render from status; no action offered that the backend would reject
- 409 stale precondition surfaces a visible refusal

Backend: tests for the standalone run endpoint, and confirmation that the extraction leaves `run_technical_pipeline()` behaviour unchanged (existing 357 must stay green).

End-to-end: merge to `master`, Vercel deploy, trigger a real audit against the live site from the AUDIT tab, walk one card through approve → mark applied → verify. Per the 2026-07-16 decision, no local Docker demo run is required.

## Out of scope

- Client-facing audit views
- RUNS tab redesign
- Retiring `/admin/approvals` and the `action_cards` table
- Community cards (the `source` column stays, unused)
- Any drafted or generated content
- Per-platform instruction branches beyond Squarespace (WordPress/repository clients fall through to the generic branch, which is correct and safe)
