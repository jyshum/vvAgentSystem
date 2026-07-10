# Product Visibility and Content Authority Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the tracker so client-facing metrics, labels, add-client onboarding, config replacement, and prompt-generation rules consistently separate Product Visibility from Content Authority while keeping the current backend bucket enum and scoring formulas.

**Architecture:** Keep the database and tracker formulas unchanged. Treat `consideration` as Product Visibility and `awareness` as Content Authority at the presentation/configuration layer, using the already-computed `bucket_scores`. Add intent JSON import to client creation and add a replace-active mode to the existing config JSON importer so bad prompt sets can be restarted without deleting historical query rows.

**Tech Stack:** Next.js 16 dashboard, TypeScript, Supabase admin/server clients, Vitest, Python tracker code already in place but not changed by this plan except where existing dirty edits must be reviewed, Markdown prompt rules.

## Global Constraints

- No bucket enum migration.
- No schema migration.
- No backend scoring formula rewrite.
- No automated prompt generation inside the app.
- No brand-specific monitoring.
- Product Visibility is the universal visible label for `consideration`.
- Content Authority is the universal visible label for `awareness`.
- Branded remains visible only as `Branded - Deferred`.
- The main dashboard score uses `bucket_scores.consideration.mention_rate`.
- Content Authority displays mention and citation signals from `bucket_scores.awareness`.
- The merged non-branded score is not presented as the main client-facing score.
- Use the existing dark editorial system: existing serif/mono hierarchy, thin borders, compact grid structure, no new cards-inside-cards, no marketing explanatory panels.
- Do not overwrite unrelated dirty files. Existing dirty files include `agents/src/graph/nodes.py`, `dashboard/app/admin/clients/[id]/layout.tsx`, `dashboard/app/admin/clients/[id]/overview/page.tsx`, `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`, `dashboard/proxy.ts`, `docs/superpowers/references/intent-generation-rules.md`, `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md`, `agents/src/__main__.py`, and `dashboard/app/mock-current/`.

---

## File Structure

**Dashboard metric labels and selection:**
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx` - client header hero score and bucket copy.
- Modify: `dashboard/app/admin/clients/[id]/overview/page.tsx` - timeline score, metric panels, labels.
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx` - run detail primary score and bucket labels.
- Modify: `dashboard/app/admin/clients/[id]/queries/page.tsx` - heat rows/groups if any visible bucket labels remain.
- Modify: `dashboard/components/admin/HeatTable.tsx` - visible group names.
- Modify: `dashboard/components/admin/QueryBucketManager.tsx` - config labels, descriptions, dropdown options, replacement mode.
- Modify: `dashboard/components/admin/AddClientModal.tsx` - add generated intent JSON import and update labels.
- Modify: `dashboard/components/admin/ClientRow.tsx`, `dashboard/app/admin/clients/page.tsx`, `dashboard/app/admin/page.tsx` - board/list score selection if they currently use merged values.
- Modify: `dashboard/components/report/KPIGrid.tsx`, `dashboard/components/admin/ReportRow.tsx` - report labels/score selection if needed.
- Test: existing dashboard tests plus new tests where behavior is pure and testable.

**Dashboard APIs:**
- Modify: `dashboard/app/api/admin/clients/route.ts` - accept optional `intents` with paraphrases on client creation.
- Modify: `dashboard/app/api/admin/queries/[clientId]/route.ts` - support `mode: "replace_active"` for JSON import.
- Test: add or extend API route tests if route-test scaffolding exists; otherwise verify through build and focused helper tests.

**Prompt rules:**
- Modify: `docs/superpowers/references/intent-generation-rules.md` - rewrite rules for Product Visibility/Content Authority using internal bucket values.

**Shared helpers:**
- Create: `dashboard/lib/intent-labels.ts` - single source of truth for visible bucket labels and bucket-score selection.
- Test: `dashboard/__tests__/intent-labels.test.ts`.

---

### Task 1: Shared Labels and Metric Helpers

**Files:**
- Create: `dashboard/lib/intent-labels.ts`
- Test: `dashboard/__tests__/intent-labels.test.ts`

**Interfaces:**
- Produces: `BUCKET_LABELS`, `BUCKET_DETAILS`, `productVisibilityScore(run)`, `contentAuthorityScore(run)`.
- Consumes: existing `TrackerRun` and `Query` types from `dashboard/lib/types.ts`.

- [ ] **Step 1: Write the failing tests**

Create `dashboard/__tests__/intent-labels.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  BUCKET_DETAILS,
  BUCKET_LABELS,
  contentAuthorityScore,
  productVisibilityScore,
} from "@/lib/intent-labels";
import type { TrackerRun } from "@/lib/types";

function runWithBuckets(bucket_scores: TrackerRun["bucket_scores"]): TrackerRun {
  return {
    id: "run-1",
    client_id: "client-1",
    ran_at: "2026-07-10T00:00:00Z",
    aggregate_mention_rate: 0.91,
    non_branded_mention_rate: 0.91,
    aggregate_avg_mention_level: 2,
    bucket_scores,
    per_engine_scores: {},
    competitor_scores: {},
    gsc_clicks: 0,
    gsc_impressions: 0,
    gsc_ctr: 0,
    gsc_position: 0,
    gsc_top_queries: [],
    discovered_competitors: [],
    query_set_signature: null,
    query_set_changed: false,
  };
}

describe("intent labels", () => {
  it("maps internal buckets to product labels", () => {
    expect(BUCKET_LABELS.consideration).toBe("Product Visibility");
    expect(BUCKET_LABELS.awareness).toBe("Content Authority");
    expect(BUCKET_LABELS.branded).toBe("Branded - Deferred");
    expect(BUCKET_DETAILS.consideration).toContain("Product");
    expect(BUCKET_DETAILS.awareness).toContain("Content");
  });

  it("uses consideration for product visibility and does not fall back to the merged score", () => {
    const run = runWithBuckets({
      consideration: { mention_rate: 0.42, avg_mention_level: 2.1, citation_rate: 0.2, intent_count: 6 },
      awareness: { mention_rate: 0.76, avg_mention_level: 2.8, citation_rate: 0.5, intent_count: 3 },
    });

    expect(productVisibilityScore(run)).toEqual({
      mention_rate: 0.42,
      avg_mention_level: 2.1,
      citation_rate: 0.2,
      intent_count: 6,
    });
  });

  it("returns null product visibility when no consideration bucket exists", () => {
    const run = runWithBuckets({
      awareness: { mention_rate: 0.76, avg_mention_level: 2.8, citation_rate: 0.5, intent_count: 3 },
    });

    expect(productVisibilityScore(run)).toBeNull();
  });

  it("uses awareness for content authority", () => {
    const run = runWithBuckets({
      awareness: { mention_rate: 0.31, avg_mention_level: 1.8, citation_rate: 0.44, intent_count: 4 },
    });

    expect(contentAuthorityScore(run)).toEqual({
      mention_rate: 0.31,
      avg_mention_level: 1.8,
      citation_rate: 0.44,
      intent_count: 4,
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd dashboard
npm test -- intent-labels.test.ts
```

Expected: FAIL because `@/lib/intent-labels` does not exist.

- [ ] **Step 3: Implement the helper**

Create `dashboard/lib/intent-labels.ts`:

```ts
import type { Query, TrackerRun } from "@/lib/types";

export const BUCKET_LABELS: Record<Query["bucket"], string> = {
  awareness: "Content Authority",
  consideration: "Product Visibility",
  branded: "Branded - Deferred",
};

export const BUCKET_DETAILS: Record<Query["bucket"], string> = {
  awareness: "Educational and how-to intents; measured as authority and citation signal",
  consideration: "Product, tool, platform, template, and resource-selection intents",
  branded: "Deferred - not measured in current runs",
};

export type BucketScore = NonNullable<TrackerRun["bucket_scores"][Query["bucket"]]>;

export function productVisibilityScore(run: Pick<TrackerRun, "bucket_scores">): BucketScore | null {
  return run.bucket_scores?.consideration ?? null;
}

export function contentAuthorityScore(run: Pick<TrackerRun, "bucket_scores">): BucketScore | null {
  return run.bucket_scores?.awareness ?? null;
}
```

- [ ] **Step 4: Verify**

Run:

```bash
cd dashboard
npm test -- intent-labels.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/intent-labels.ts dashboard/__tests__/intent-labels.test.ts
git commit -m "feat: add product visibility bucket helpers"
```

---

### Task 2: Dashboard Score Selection and Labels

**Files:**
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx`
- Modify: `dashboard/app/admin/clients/[id]/overview/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/runs/[runId]/page.tsx`
- Modify: `dashboard/app/admin/clients/[id]/queries/page.tsx`
- Modify: `dashboard/components/admin/HeatTable.tsx`
- Modify: `dashboard/components/admin/ClientRow.tsx`
- Modify: `dashboard/app/admin/clients/page.tsx`
- Modify: `dashboard/app/admin/page.tsx`
- Modify: `dashboard/components/report/KPIGrid.tsx`
- Modify: `dashboard/components/admin/ReportRow.tsx`
- Test: existing dashboard tests; add component/helper tests only where practical.

**Interfaces:**
- Consumes: `BUCKET_LABELS`, `productVisibilityScore`, `contentAuthorityScore`.
- Produces: main client-facing score uses `bucket_scores.consideration.mention_rate`; visible labels use Product Visibility / Content Authority.

- [ ] **Step 1: Audit all merged-score and old-label usage**

Run:

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
rg -n "non_branded_mention_rate|aggregate_mention_rate|Awareness|Consideration|awareness|consideration|Query Buckets|AI Visibility|Non-Branded Mention Rate" dashboard/app dashboard/components dashboard/lib
```

Expected: collect the remaining frontend surfaces that need product-label mapping. Do not edit yet.

- [ ] **Step 2: Update existing tests where labels are asserted**

Search tests:

```bash
cd dashboard
rg -n "Awareness|Consideration|Non-Branded|AI Visibility|Product Visibility|Content Authority" __tests__
```

Update any tests that expect visible labels to expect `Product Visibility` and `Content Authority`.

- [ ] **Step 3: Run focused tests to verify failure**

Run:

```bash
cd dashboard
npm test
```

Expected: FAIL if label tests were updated before UI changes. If no tests cover those labels, continue and rely on build plus visual/code review for this presentational pass.

- [ ] **Step 4: Update score selection**

In dashboard pages/components:

- Replace main score reads from `latest.non_branded_mention_rate ?? latest.aggregate_mention_rate` with `productVisibilityScore(latest)?.mention_rate ?? null`.
- Replace primary sparkline values with Product Visibility values where `bucket_scores.consideration` exists.
- For Content Authority panels, read `contentAuthorityScore(latest)?.mention_rate` and `.citation_rate`.
- If Product Visibility is missing, render the existing empty/pending style with copy like `product visibility pending`.
- Do not use `aggregate_mention_rate` or `non_branded_mention_rate` as a visible fallback for the main score.

Use imports:

```ts
import { BUCKET_LABELS, contentAuthorityScore, productVisibilityScore } from "@/lib/intent-labels";
```

- [ ] **Step 5: Update visible labels**

Replace visible copy:

- `Awareness` -> `Content Authority`
- `Consideration` -> `Product Visibility`
- `Branded` group label -> `Branded - Deferred` where the label itself appears; if a compact table needs `Branded`, pair it with `deferred / not measured`.
- `Query Buckets` -> `Tracked Intents` or `Intent Set`.
- `Awareness and consideration intents are measured. Branded monitoring is deferred.` -> `Product Visibility and Content Authority intents are measured separately. Branded monitoring is deferred.`
- `Non-Branded Mention Rate` -> `Product Visibility`.

- [ ] **Step 6: Verify**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
npx tsc --noEmit
```

Expected: tests pass, lint has 0 errors, build passes, TypeScript passes.

- [ ] **Step 7: Commit**

```bash
git add dashboard/app dashboard/components dashboard/lib dashboard/__tests__
git commit -m "feat: present product visibility and content authority metrics"
```

Before committing, run:

```bash
git diff --cached --name-only
```

Expected: do not stage `dashboard/proxy.ts`, `dashboard/app/mock-current/`, or `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md`.

---

### Task 3: Add Client Intent JSON Import

**Files:**
- Modify: `dashboard/components/admin/AddClientModal.tsx`
- Modify: `dashboard/app/api/admin/clients/route.ts`
- Optional helper: `dashboard/lib/intent-import.ts`
- Test: add focused tests if route/helper test scaffolding exists.

**Interfaces:**
- Consumes: JSON intent shape `{ prompt_text, bucket, paraphrases }`.
- Produces: `POST /api/admin/clients` accepts optional `intents` and inserts `queries.paraphrases` rows during client creation.

- [ ] **Step 1: Write/import validation tests if helper is created**

If creating `dashboard/lib/intent-import.ts`, add `dashboard/__tests__/intent-import.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { parseIntentJson } from "@/lib/intent-import";

describe("parseIntentJson", () => {
  it("parses product visibility and content authority intents", () => {
    expect(parseIntentJson(JSON.stringify([
      { prompt_text: "best budgeting app", bucket: "consideration", paraphrases: ["budgeting app for med students"] },
      { prompt_text: "how to budget", bucket: "awareness", paraphrases: ["budgeting tips"] },
    ]))).toEqual([
      { prompt_text: "best budgeting app", bucket: "consideration", paraphrases: ["budgeting app for med students"] },
      { prompt_text: "how to budget", bucket: "awareness", paraphrases: ["budgeting tips"] },
    ]);
  });

  it("rejects invalid buckets", () => {
    expect(() => parseIntentJson(JSON.stringify([
      { prompt_text: "best budgeting app", bucket: "product_visibility", paraphrases: [] },
    ]))).toThrow("invalid bucket");
  });

  it("rejects non-string paraphrases", () => {
    expect(() => parseIntentJson(JSON.stringify([
      { prompt_text: "best budgeting app", bucket: "consideration", paraphrases: [7] },
    ]))).toThrow("paraphrases");
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd dashboard
npm test -- intent-import.test.ts
```

Expected: FAIL if helper does not exist.

- [ ] **Step 3: Implement shared client-side parser if needed**

Create `dashboard/lib/intent-import.ts`:

```ts
import type { Query } from "@/lib/types";

const BUCKETS = new Set<Query["bucket"]>(["awareness", "consideration", "branded"]);

export interface IntentImportItem {
  prompt_text: string;
  bucket: Query["bucket"];
  paraphrases: string[];
}

export function normalizeIntent(input: unknown): IntentImportItem {
  if (!input || typeof input !== "object") throw new Error("each intent must be an object");
  const row = input as Record<string, unknown>;
  if (typeof row.prompt_text !== "string" || !row.prompt_text.trim()) {
    throw new Error("each intent needs prompt_text");
  }
  const bucket = row.bucket === undefined ? "consideration" : row.bucket;
  if (typeof bucket !== "string" || !BUCKETS.has(bucket as Query["bucket"])) {
    throw new Error(`invalid bucket: ${String(bucket)}`);
  }
  const paraphrases = row.paraphrases ?? [];
  if (!Array.isArray(paraphrases) || paraphrases.some((x) => typeof x !== "string" || !x.trim())) {
    throw new Error("paraphrases must be an array of non-empty strings");
  }
  return {
    prompt_text: row.prompt_text.trim(),
    bucket: bucket as Query["bucket"],
    paraphrases: paraphrases.map((x) => x.trim()),
  };
}

export function parseIntentJson(text: string): IntentImportItem[] {
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed)) throw new Error("Expected a JSON array");
  return parsed.map(normalizeIntent);
}
```

- [ ] **Step 4: Update Add Client modal**

In `dashboard/components/admin/AddClientModal.tsx`:

- Remove `awarenessPrompts`, `considerationPrompts`, and `brandedPrompts` state and TagInput blocks.
- Add:

```ts
const [intentJson, setIntentJson] = useState("");
```

- Before submit, parse non-empty JSON:

```ts
let intents: IntentImportItem[] = [];
if (intentJson.trim()) {
  try {
    intents = parseIntentJson(intentJson);
  } catch (err) {
    setError(err instanceof Error ? err.message : "Intent JSON is invalid.");
    return;
  }
}
```

- Submit `intents`:

```ts
body: JSON.stringify({
  name: name.trim(),
  brand_name: brandName.trim() || name.trim(),
  website_domain: domain.trim(),
  brand_variations: brandVariations,
  intents,
  competitors,
})
```

- Add a visible textarea labeled `Generated Intent Set JSON`.
- Placeholder must use internal bucket values and visible product examples.
- Keep the modal styling restrained: existing border/input treatment, mono label, serif body where already used.

- [ ] **Step 5: Update create-client API**

In `dashboard/app/api/admin/clients/route.ts`:

- Accept `intents` from body.
- Validate `intents` with server-side logic equivalent to `normalizeIntent`; do not trust the client parser.
- Insert rows with `paraphrases`.
- Keep `query_buckets` backward compatibility.

Implementation shape:

```ts
const { name, brand_name, website_domain, brand_variations, target_queries, query_buckets, intents, competitors } = body;
const intentRows = buildIntentRows(intents);
const bucketPrompts = buildBucketPrompts(query_buckets);
const prompts = intentRows.length > 0
  ? intentRows
  : bucketPrompts.length > 0
    ? bucketPrompts
    : legacyPrompts.map((prompt_text) => ({ prompt_text, bucket: "consideration", paraphrases: [] }));
```

Insert:

```ts
prompts.map(({ prompt_text, bucket, paraphrases }) => ({
  client_id: data.id,
  prompt_text,
  slug: generateSlug(prompt_text),
  bucket,
  set_type: "core",
  paraphrases,
}))
```

- [ ] **Step 6: Verify**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add dashboard/components/admin/AddClientModal.tsx dashboard/app/api/admin/clients/route.ts dashboard/lib/intent-import.ts dashboard/__tests__/intent-import.test.ts
git commit -m "feat: import generated intents when adding clients"
```

If no helper/test was created, omit those paths from `git add`.

---

### Task 4: Config Replace-Active Import

**Files:**
- Modify: `dashboard/app/api/admin/queries/[clientId]/route.ts`
- Modify: `dashboard/components/admin/QueryBucketManager.tsx`
- Optional helper reuse: `dashboard/lib/intent-import.ts`
- Test: focused parser/helper tests plus dashboard build.

**Interfaces:**
- Consumes: existing POST body `{ intents: [...] }`.
- Produces: POST supports `{ intents: [...], mode: "append" | "replace_active" }`.

- [ ] **Step 1: Add validation-first API behavior**

In `dashboard/app/api/admin/queries/[clientId]/route.ts`, refactor bulk import:

```ts
const mode = body?.mode === "replace_active" ? "replace_active" : "append";
```

Validation must build all `rows` before any database write. Keep existing validation rules.

When `mode === "replace_active"`:

```ts
const retiredAt = new Date().toISOString();
const { error: retireError } = await admin
  .from("queries")
  .update({ status: "retired", retired_at: retiredAt })
  .eq("client_id", clientId)
  .eq("status", "active");
if (retireError) return Response.json({ error: retireError.message }, { status: 500 });
```

Then insert the new rows.

- [ ] **Step 2: Update QueryBucketManager UI**

In `dashboard/components/admin/QueryBucketManager.tsx`:

- Keep the existing collapsed JSON importer.
- Add a checkbox/toggle:

```txt
Replace active intent set
```

- When checked, submit:

```ts
body: JSON.stringify({ intents, mode: "replace_active" })
```

- After successful replace, set local `queries` state to keep retired existing rows out of active display and add created rows:

```ts
setQueries((current) =>
  replaceActive
    ? [...current.map((q) => q.status === "active" ? { ...q, status: "retired" as const } : q), ...created]
    : [...current, ...created]
);
```

- Button copy should change from `Import Intents` to `Replace Intent Set` when checked.
- Include a short inline warning in the existing style: `Current active intents will be retired before import.`

- [ ] **Step 3: Verify replace mode does not retire on invalid JSON**

Manual code review requirement: JSON parsing and validation must happen before the fetch; server validation must happen before retire. Document this in the final task summary.

- [ ] **Step 4: Verify**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add 'dashboard/app/api/admin/queries/[clientId]/route.ts' dashboard/components/admin/QueryBucketManager.tsx dashboard/lib/intent-import.ts dashboard/__tests__/intent-import.test.ts
git commit -m "feat: replace active intent set from config"
```

If helper/test unchanged from Task 3, omit those paths.

---

### Task 5: Prompt Generation Rules

**Files:**
- Modify: `docs/superpowers/references/intent-generation-rules.md`

**Interfaces:**
- Consumes: approved semantic mapping.
- Produces: an operator prompt that returns valid JSON with Product Visibility as `consideration` and Content Authority as `awareness`.

- [ ] **Step 1: Rewrite the rules doc**

Update `docs/superpowers/references/intent-generation-rules.md` so it says:

- Product Visibility uses internal bucket `"consideration"`.
- Content Authority uses internal bucket `"awareness"`.
- Target count: 5-6 Product Visibility intents and 3-4 Content Authority intents.
- Target paraphrases: 5 per intent.
- Total expected calls: roughly `9 intents x 6 wordings x 4 engines = 216 calls`.
- The model must not output `product_visibility` or `content_authority` bucket values.
- Include good/bad examples for BudgetYourMD-style medical-student finance prompts.
- Include review checklist that catches off-topic content authority prompts.

Preserve useful existing sections:

- Manual/off-platform generation.
- No client or competitor brand names in unbranded prompts.
- Grounding in website and GSC.
- Paste-ready JSON output.

- [ ] **Step 2: Self-review the doc**

Run:

```bash
rg -n "product_visibility|content_authority|Awareness|Consideration|8 diverse|6-12|Both buckets combine|single AI visibility score" docs/superpowers/references/intent-generation-rules.md
```

Expected:

- `product_visibility` and `content_authority` only appear as forbidden bucket values if at all.
- No old claim says both buckets combine into a single headline score.
- No old target says ~8 paraphrases if the new target is 5.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/references/intent-generation-rules.md
git commit -m "docs: update intent generation rules for product visibility"
```

---

### Task 6: Final Verification and Dirty-File Safety

**Files:**
- No code changes unless verification finds a defect.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: verified branch ready to push/merge.

- [ ] **Step 1: Full dashboard verification**

Run:

```bash
cd dashboard
npm test
npm run lint
npm run build
npx tsc --noEmit
```

Expected: tests pass, lint has 0 errors, build passes, TypeScript passes.

- [ ] **Step 2: Backend smoke verification**

Run:

```bash
cd agents
.venv/bin/python -m pytest tests/test_intent_aggregation.py tests/test_graph_nodes.py -q
```

Expected: pass. Full backend suite is not required for this frontend/config polish unless backend files changed beyond docs/API routes.

- [ ] **Step 3: Dirty file audit**

Run:

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
git status --short
git diff --name-only
```

Expected:

- Implementation commits should not include `dashboard/proxy.ts`, `dashboard/app/mock-current/`, or `docs/superpowers/specs/2026-07-03-improvement-pipeline-design.md` unless the user separately approves cleanup.
- If pre-existing dirty files remain, list them explicitly in the final summary.

- [ ] **Step 4: Final grep audit**

Run:

```bash
rg -n "Awareness|Consideration|Non-Branded Mention Rate|non-branded mention rate|single AI visibility score|Both buckets combine" dashboard docs/superpowers/references/intent-generation-rules.md
```

Expected: no stale client-facing labels remain, except internal code comments or historical docs outside the current rules doc.

---

## Self-Review

- Spec coverage: tasks cover dashboard labels/score selection, add-client JSON import, config replace-active import, prompt rules, and final verification.
- No schema/backend scoring rewrite is planned.
- The plan intentionally allows current dirty files to exist but requires staging only task files.
- The only likely ambiguity is exactly how many dashboard surfaces should hide the composite score; Task 2 resolves this by replacing client-facing main score surfaces and leaving internal data untouched.
