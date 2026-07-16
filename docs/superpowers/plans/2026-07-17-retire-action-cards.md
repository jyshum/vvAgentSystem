# Retire the action_cards Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the dead `action_cards` UI surface and repoint the admin board's "cards awaiting" signal at the live `technical_audit_action_cards` table, so the board stops silently reporting every client as healthy.

**Architecture:** Deletion plus one data-source swap. `opsBadge()` in `lib/derive.ts` is already source-agnostic (it takes `pendingCount`/`oldestPendingDays` as plain numbers), so the board only needs a different query feeding it - no change to the badge logic itself.

**Tech Stack:** Next.js 16.2.9 (App Router, RSC), React 19.2.4, Tailwind v4, Vitest 4 + @testing-library/react, Supabase JS.

---

## Context

Migration `017_remove_legacy_runtime.sql:1` **drops `public.action_cards`**, along with `page_citation_scores`, `query_page_matches`, `page_inventory`, and `client_site_profiles`. This was verified against production on 2026-07-16 via the REST API:

```
action_cards            -> HTTP 404   (does not exist)
page_citation_scores    -> HTTP 404   (does not exist)
query_page_matches      -> HTTP 404   (does not exist)
technical_audit_action_cards -> HTTP 200
technical_audit_finding_groups -> HTTP 200
```

Six places in the dashboard still query `action_cards`. None crash: the code destructures `data` and ignores `error`, so a missing table reads as "no rows". The consequences are silent and worse than a crash:

- **`app/admin/page.tsx`** feeds `pendingCount: pending.length` into `opsBadge()`. With the table gone that is permanently `0`, so `opsBadge` never returns `kind: "waiting"` and **the board reports every client HEALTHY unconditionally**.
- **`app/admin/clients/[id]/queries/page.tsx`** shows per-query pending counts: always 0.
- **`app/admin/approvals/`** is a zombie - a live top-level nav item that can never display a row again. Nothing has written `action_cards` since the legacy engine was deleted in commit `375906c`, and the new cards live in a different table it does not read.
- **`app/api/admin/approve/route.ts`** writes approve/reject to a dropped table.

The replacement signal already exists. `technical_audit_action_cards` is live and populated by `build_cards()` in `agents/src/technical_audit/workflow.py`. Open work is any card **not** in a terminal state - the AUDIT page already defines this as `!["rejected", "verified"].includes(card.status)` (`app/admin/clients/[id]/audit/page.tsx`). Reuse that definition; do not invent a second one.

**Prior context:** the 2026-07-16 technical-audit frontend cutover deliberately fenced off `/admin/approvals`, the board, and RUNS, on the reasoning that approvals was "live and deep-linked". That reasoning was incomplete - it never checked whether the table still existed. This plan is that deferred work, now justified.

---

## Critical Context For Someone New

1. **No new dependencies.** `dashboard/package.json` has React, Next, Supabase and nothing else. No shadcn, no Radix, no icon library, no Motion. Do not `npm install`.
2. **No scores.** The scoring engine was deleted; a `/100` badge contradicts the architecture. Do not add one, do not resurrect one.
3. **No em-dashes in user-visible strings.** Use a hyphen.
4. **Colors are inline CSS-variable styles**, not utility classes: `style={{ color: "var(--mute)" }}`. Tokens in `app/globals.css`. Sharp corners, dark theme only.
5. **`rm -rf .next` before `npx tsc --noEmit`.** A stale `.next/types/` accumulates duplicate generated files with a `" 3"` suffix that tsc reports as phantom duplicate-identifier errors. From a clean `.next`, expect **zero** errors.
6. **This plan DOES touch RUNS and the board.** That is intentional and is the difference from the previous plan. It is scoped to removing `action_cards` reads and dead links only - do not redesign those pages.

**Commands:**
- Frontend tests: `cd dashboard && npm test` (baseline **135 passing**)
- Backend tests: `cd agents && .venv/bin/python -m pytest -q` (baseline **367 passing**; this plan should not change it)
- Lint: `cd dashboard && npm run lint` - there is ONE pre-existing error in `components/admin/TriggerRunButton.tsx:89` (`react-hooks/set-state-in-effect`) that is NOT yours. Do not fix it; do not add new ones.

---

## File Structure

**Delete:**
| Path | Why |
|---|---|
| `app/admin/approvals/` | zombie inbox over a dropped table |
| `components/approvals/` | its components (`AutomatedCard`, `BriefCard`, `CommunityCheckCard`, `CrawlabilityCard`, `InboxGroup`, `CardHighlighter`, `card-shared`) |
| `app/api/admin/approve/` | writes to a dropped table |
| `__tests__/components/approval-cards.test.tsx` | tests deleted code |
| `__tests__/components/card-highlighter.test.tsx` | tests deleted code |

**Modify:**
| Path | Change |
|---|---|
| `app/admin/page.tsx` | swap the two `action_cards` reads for one `technical_audit_action_cards` read |
| `components/board/BoardRow.tsx` | badge links to the client's AUDIT tab, not `/admin/approvals` |
| `components/admin/NavLinks.tsx` | drop the APPROVALS entry |
| `app/admin/clients/[id]/queries/page.tsx` | remove the per-query `action_cards` count |
| `components/admin/HeatTable.tsx` | remove `approvalsHref` and its links |
| `app/admin/clients/[id]/runs/[runId]/page.tsx` | remove the `action_cards` read |
| `lib/run-presentation.ts` | remove the `/admin/approvals` href |
| `lib/improvement-types.ts` | remove the `ActionCard` type |
| `__tests__/components/heat-table.test.tsx`, `__tests__/run-presentation.test.ts` | update expectations |

**Unchanged:** `lib/derive.ts` - `opsBadge()` is source-agnostic and correct as-is.

---

## Task 1: Repoint the board at audit cards

**Files:**
- Modify: `dashboard/app/admin/page.tsx`
- Test: `dashboard/__tests__/derive.test.ts` (verify only; do not change `derive.ts`)

**Context:** `app/admin/page.tsx:34-43` runs two `action_cards` queries per client (`status=pending`, `status=implemented`) inside a `Promise.all`. Line ~71 feeds `pendingCount: pending.length` into `opsBadge()`; line ~108 sums `totalCards`. Read the whole file first - the queries sit in a per-client `Promise.all` whose destructuring order matters.

- [ ] **Step 1: Read the file and map the shape**

Run: `cd dashboard && sed -n 1,120p app/admin/page.tsx`

Identify: what `pending` and `implemented` are destructured to, every use of each, and what `totalCards` feeds.

- [ ] **Step 2: Swap the query**

Replace the two `action_cards` queries with ONE query for open audit cards. Open = not terminal, matching the AUDIT page's existing definition:

```ts
supabase
  .from("technical_audit_action_cards")
  .select("id, created_at")
  .eq("client_id", client.id)
  .not("status", "in", "(verified,rejected)"),
```

Keep `pendingCount: pending.length` and the `oldestPendingDays` computation working against the new rows (`created_at` still exists on the new table, so the age math is unchanged).

If `implemented` is used for anything, replace it with a count of `status=verified` on the new table. If it is unused once `action_cards` is gone, delete it rather than keep a dead variable - check every reference first.

- [ ] **Step 3: Verify the badge fires**

Run: `cd dashboard && npx vitest run __tests__/derive.test.ts`
Expected: PASS unchanged. `derive.ts` is untouched; this confirms you did not disturb the badge contract.

- [ ] **Step 4: Typecheck**

Run: `cd dashboard && rm -rf .next && npx tsc --noEmit`
Expected: zero errors.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/admin/page.tsx
git commit -m "fix: source the board ops badge from technical audit cards"
```

---

## Task 2: Point the board badge at the AUDIT tab

**Files:**
- Modify: `dashboard/components/board/BoardRow.tsx`

**Context:** `BoardRow.tsx:164` reads:
```tsx
{badge.kind === "waiting" ? <Link href="/admin/approvals">{badgeChip}</Link> : badgeChip}
```
`/admin/approvals` is deleted in Task 5. The badge means "this client has open cards", so it should lead to that client's AUDIT tab.

- [ ] **Step 1: Confirm the client id is available**

Run: `cd dashboard && sed -n 1,40p components/board/BoardRow.tsx`
The props interface has `pendingCount: number` at line ~16. Confirm a client id field exists (the row must know which client it renders). If it does NOT, STOP and report - do not invent a prop without checking how the parent builds rows.

- [ ] **Step 2: Repoint the link**

```tsx
{badge.kind === "waiting" ? (
  <Link href={`/admin/clients/${clientId}/audit`}>{badgeChip}</Link>
) : (
  badgeChip
)}
```
Use whatever the actual client-id prop is named.

- [ ] **Step 3: Typecheck and commit**

Run: `cd dashboard && rm -rf .next && npx tsc --noEmit`

```bash
git add dashboard/components/board/BoardRow.tsx
git commit -m "fix: link the board ops badge to the client audit tab"
```

---

## Task 3: Remove per-query card counts

**Files:**
- Modify: `dashboard/app/admin/clients/[id]/queries/page.tsx`
- Modify: `dashboard/components/admin/HeatTable.tsx`
- Test: `dashboard/__tests__/components/heat-table.test.tsx`

**Context:** `queries/page.tsx:54-60` queries `action_cards` by `query_id`. **The new audit cards have no `query_id`** - they are grounded in a page/finding, not a query (see `supabase/migrations/018_technical_audit_workflow.sql`). So this signal cannot be repointed; it must be removed. `HeatTable.tsx:35-37` has `approvalsHref(queryId)` linking cells to the inbox.

- [ ] **Step 1: Write the failing test**

In `dashboard/__tests__/components/heat-table.test.tsx`, the existing test at line ~36 asserts:
```ts
expect(badges.at(-1)!.getAttribute("href")).toBe("/admin/approvals?query=query-1");
```
Change it to assert the badge is **no longer a link** - it renders as plain content with no `href` to the deleted route. Write the assertion to match the shape you intend to ship.

- [ ] **Step 2: Run it and watch it fail**

Run: `cd dashboard && npx vitest run __tests__/components/heat-table.test.tsx`
Expected: FAIL, because the link is still rendered.

- [ ] **Step 3: Remove the link and the count**

Delete `approvalsHref` from `HeatTable.tsx` and render the chip without a link. Remove the `action_cards` query from `queries/page.tsx` and every prop threaded from it into `HeatTable`. Follow the data through - do not leave an always-empty prop dangling.

- [ ] **Step 4: Verify**

Run: `cd dashboard && npx vitest run __tests__/components/heat-table.test.tsx && rm -rf .next && npx tsc --noEmit`
Expected: PASS, zero tsc errors.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/admin/clients/\[id\]/queries/page.tsx dashboard/components/admin/HeatTable.tsx dashboard/__tests__/components/heat-table.test.tsx
git commit -m "refactor: remove per-query action card counts"
```

---

## Task 4: Remove the run-detail read and the crawlability CTA

**Files:**
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`
- Modify: `dashboard/lib/run-presentation.ts`
- Test: `dashboard/__tests__/run-presentation.test.ts`

**Context:** `runs/[runId]/page.tsx:87` reads `action_cards` for the run. `run-presentation.ts:60` returns `href: "/admin/approvals"` with `ctaLabel: "VIEW FIX-CRAWLABILITY CARD →"` - a CTA for the crawlability card concept, whose backend (`agents/src/improvement/crawlability.py`) was deleted in `375906c`. The card it points at cannot exist.

**Scope discipline:** remove the dead read and the dead CTA. Do NOT redesign the run-detail page or the legacy funnel. That is separate work.

- [ ] **Step 1: Update the presentation test**

`__tests__/run-presentation.test.ts:157` asserts `href: "/admin/approvals"`. Decide the replacement and write it first:
- If the crawlability banner still has a useful destination, point it at the client's AUDIT tab.
- If the CTA has no meaningful target, remove `ctaLabel`/`href` from that branch and keep the diagnostic text.

Read `crawlabilityBannerPresentation()` in full before choosing, and state your reasoning in the commit message.

- [ ] **Step 2: Watch it fail, then implement**

Run: `cd dashboard && npx vitest run __tests__/run-presentation.test.ts`
Expected: FAIL for the right reason.

Then remove the `action_cards` query from `runs/[runId]/page.tsx:87` and every use of its result. Trace each one - if a tile renders a card count, that tile is reporting a permanent zero and should go with it.

- [ ] **Step 3: Verify**

Run: `cd dashboard && npx vitest run __tests__/run-presentation.test.ts && rm -rf .next && npx tsc --noEmit && npm test`

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/admin/clients/\[id\]/runs dashboard/lib/run-presentation.ts dashboard/__tests__/run-presentation.test.ts
git commit -m "refactor: remove dead action card reads from run detail"
```

---

## Task 5: Delete the approvals surface

**Files:**
- Delete: `dashboard/app/admin/approvals/`, `dashboard/components/approvals/`, `dashboard/app/api/admin/approve/`
- Delete: `dashboard/__tests__/components/approval-cards.test.tsx`, `dashboard/__tests__/components/card-highlighter.test.tsx`
- Modify: `dashboard/components/admin/NavLinks.tsx`
- Modify: `dashboard/lib/improvement-types.ts`

**This is destructive. Verify before deleting.**

- [ ] **Step 1: Re-verify nothing outside the deletion set still references these**

```bash
cd dashboard && grep -rn "admin/approvals\|components/approvals\|ActionCard\b\|api/admin/approve" --include="*.ts" --include="*.tsx" app components lib __tests__ | grep -v "^app/admin/approvals/" | grep -v "^components/approvals/" | grep -v "^app/api/admin/approve/" | grep -v "components/audit/ActionCard"
```
Expected: **no output** once Tasks 1-4 are done. If anything remains, fix that reference first. Note `components/audit/ActionCard.tsx` is the NEW audit card and must survive - do not delete it.

- [ ] **Step 2: Remove APPROVALS from nav**

`components/admin/NavLinks.tsx:6-10` - delete the `{ label: "APPROVALS", href: "/admin/approvals", exact: false }` entry, leaving BOARD and CLIENTS.

- [ ] **Step 3: Delete**

```bash
cd dashboard
git rm -r app/admin/approvals components/approvals app/api/admin/approve
git rm __tests__/components/approval-cards.test.tsx __tests__/components/card-highlighter.test.tsx
```

- [ ] **Step 4: Remove the dead type**

In `lib/improvement-types.ts`, remove the `ActionCard` interface and any type now referenced by nothing (`PageCitationScore`, `QueryPageMatch`, `CheckResult.score` are all backed by dropped tables - check each with grep before removing, and remove only what is genuinely unreferenced).

- [ ] **Step 5: Verify**

Run: `cd dashboard && rm -rf .next && npx tsc --noEmit && npm run lint && npm test && npm run build`
Expected: tsc zero errors; lint fails ONLY on the pre-existing `TriggerRunButton.tsx:89`; build passes.

Confirm in the build route list: `/admin/approvals` is **GONE**, `/admin/clients/[id]/audit` is **PRESENT**.

- [ ] **Step 6: Commit**

```bash
git commit -m "refactor: retire the action_cards approvals surface"
```

---

## Task 6: Full verification

- [ ] **Step 1: No `action_cards` references remain**

```bash
cd dashboard && grep -rn "action_cards" --include="*.ts" --include="*.tsx" app components lib __tests__
```
Expected: **no output**.

- [ ] **Step 2: No links to the deleted route**

```bash
cd dashboard && grep -rn "admin/approvals" --include="*.ts" --include="*.tsx" app components lib __tests__
```
Expected: **no output**.

- [ ] **Step 3: Suites, types, lint, build**

```bash
cd dashboard && rm -rf .next && npx tsc --noEmit && npm run lint && npm test && npm run build
cd ../agents && .venv/bin/python -m pytest -q
```
Expected: tsc zero errors; frontend suite green (count will drop from 135 as deleted-code tests go - report the actual number and name which files went); backend **367** unchanged (this plan touches no Python).

- [ ] **Step 4: No new dependencies**

```bash
cd dashboard && git diff origin/master -- package.json package-lock.json
```
Expected: **no output**.

- [ ] **Step 5: Report honestly**

State what passed and what did not, with real output. If a test was deleted, say which and why. Do not describe work as complete if a gate failed.

---

## End-to-end verification

Push to `master` (Vercel auto-deploys; this plan touches no `agents/**`, so Railway will not redeploy). Then:

1. Open `/admin` - the board should now show a **"N CARDS"** badge on any client with open audit cards, instead of HEALTHY for everyone.
2. Click that badge - it should land on that client's AUDIT tab.
3. Confirm APPROVALS is gone from the top nav and `/admin/approvals` 404s.
4. Confirm the QUERIES tab and run-detail render without the always-zero card counts.

The board telling the truth again is the whole point of this work. If the badge still says HEALTHY on a client that has open cards in the AUDIT tab, Task 1 is wrong.

---

## Notes for the implementer

- If a test fails after a change, decide honestly: did it encode the OLD behaviour (update it, and say why the new expectation is more correct), or did you break something real (stop and report)? Do not make a test green just to make it green.
- Before trusting any green test you wrote, confirm it fails against the unfixed code. Several tests on this project turned out to pass vacuously, and one appeared to prove a guard while short-circuiting before ever reaching it.
- `components/audit/**` and `lib/technical-audit-*.ts` are the NEW system. They must not be touched by this work except where they are the correct link target.
