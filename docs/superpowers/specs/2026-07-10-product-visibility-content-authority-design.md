# Product Visibility and Content Authority Tracking - Design Spec

**Date:** 2026-07-10
**Status:** Approved brainstorm
**Scope:** Lightweight tracker polish across dashboard labels, metric selection, add-client intent import, config intent replacement, and prompt-generation rules. No schema migration and no backend scoring rewrite.

---

## Goal

Make the tracker's client-facing language and onboarding flow match the two real signals we want to measure:

- **Product Visibility**: whether AI engines mention/recommend the client when buyers ask product, tool, platform, or resource-selection questions.
- **Content Authority**: whether AI engines mention/cite the client when buyers ask educational or how-to questions.

The backend already computes bucket-level metrics separately. This spec changes how those existing values are labeled, selected, and configured so the product no longer presents the merged non-branded score as the main client-facing metric.

## Current Backend Reality

The database bucket enum remains:

- `consideration`
- `awareness`
- `branded`

These values are already tracked separately in:

- `tracker_runs.bucket_scores.consideration`
- `tracker_runs.bucket_scores.awareness`
- `tracker_runs.bucket_scores.branded`
- `prompt_scores.bucket`
- `competitive_gaps.bucket`
- `tracker_results.bucket`

Each bucket score already includes:

```ts
{
  mention_rate: number;
  avg_mention_level: number;
  citation_rate: number;
  intent_count: number;
}
```

The merged values still exist:

- `aggregate_mention_rate`
- `non_branded_mention_rate`
- `aggregate_avg_mention_level`
- `aggregate_citation_rate`
- `per_engine_scores`
- `competitor_scores`

Those merged values combine `awareness` and `consideration` because `agents/src/tracker.py` defines:

```py
NON_BRANDED_BUCKETS = ("awareness", "consideration")
```

This spec does not remove or rewrite those merged values. It stops using the merged mention rate as the main client-facing score.

## Semantic Mapping

Keep internal bucket values unchanged, but relabel them everywhere humans configure or interpret the tracker:

| Internal bucket | Visible label | Meaning | Primary metric |
| --- | --- | --- | --- |
| `consideration` | Product Visibility | Buyer asks for tools, products, platforms, resources, or shortlists. The useful question is whether the client appears as a recommended option. | `bucket_scores.consideration.mention_rate` |
| `awareness` | Content Authority | Buyer asks educational, how-to, definition, planning, or problem-context questions. The useful question is whether the client is mentioned or cited as a useful authority. | `bucket_scores.awareness.mention_rate` and `bucket_scores.awareness.citation_rate` |
| `branded` | Branded - Deferred | Brand-specific recall/reputation prompts. Not fired in v1. | Not measured |

Do not introduce `product_visibility` or `content_authority` as database values in this pass.

## Dashboard Metric Presentation

### Main Score

The biggest client-facing score should be **Product Visibility**:

```ts
run.bucket_scores?.consideration?.mention_rate
```

If no consideration/product-visibility intents exist, show an empty/pending state rather than falling back to the merged composite.

### Secondary Score

Show **Content Authority** as a secondary signal:

```ts
run.bucket_scores?.awareness?.mention_rate
run.bucket_scores?.awareness?.citation_rate
```

Content Authority should not visually compete with Product Visibility as the headline metric. It should read as a separate signal: "AI engines recognize/cite the client's content for educational questions."

### Hidden Composite

Hide `non_branded_mention_rate` and `aggregate_mention_rate` from the main client-facing dashboard surfaces for now. They can remain in the database and be used internally, but should not be presented as "the" visibility score.

If an internal/admin-only diagnostic needs it later, label it as **Composite Visibility** and make clear it mixes Product Visibility and Content Authority. That is out of scope for this pass.

### Bucket Labels

Replace visible labels:

- `Awareness` -> `Content Authority`
- `Consideration` -> `Product Visibility`
- `Branded` -> `Branded - Deferred`

This applies to:

- Client overview
- Client header
- Run detail
- Query/intent heat table
- Config query manager
- Add-client modal
- Report KPI surfaces
- Any empty/pending labels or dropdown options

## Add Client Flow

The add-client modal currently supports only plain prompt tag inputs:

- awareness prompt strings
- consideration prompt strings
- branded prompt strings

Those are insufficient because they cannot create paraphrases. The client creation flow should support the same JSON intent shape used by the Config page.

### Required Add Client Behavior

Keep the basic fields:

- Client name
- Brand name
- Website domain
- Brand variations
- Competitors

Replace the old prompt tag inputs with one optional, visible-by-default textarea:

**Generated Intent Set JSON**

It accepts:

```json
[
  {
    "prompt_text": "best budgeting app for medical students",
    "bucket": "consideration",
    "paraphrases": [
      "best personal finance app for med students",
      "budgeting tools for Canadian medical students"
    ]
  },
  {
    "prompt_text": "how to budget as a medical student",
    "bucket": "awareness",
    "paraphrases": [
      "medical student budgeting tips",
      "how can med students manage money"
    ]
  }
]
```

If the textarea is empty, create the client with no intents.

If populated, create the client and insert all intents in the same submission.

### API Behavior

`POST /api/admin/clients` should accept:

```ts
{
  name: string;
  brand_name?: string;
  website_domain: string;
  brand_variations?: string[];
  competitors?: string[];
  intents?: Array<{
    prompt_text: string;
    bucket?: "awareness" | "consideration" | "branded";
    paraphrases?: string[];
  }>;
}
```

Validation should match the existing query import endpoint:

- `prompt_text` must be a non-empty string.
- `bucket`, if provided, must be one of the existing DB enum values.
- `paraphrases`, if provided, must be an array of non-empty strings.
- Default bucket is `consideration`.
- Insert `paraphrases` into `queries.paraphrases`.

The old `query_buckets` payload can remain supported for backward compatibility, but the modal should stop using it.

## Config Intent Replacement

The Config page's existing JSON importer should remain. Do not redesign it into a multi-step flow in this pass.

Add a replace mode for restarting a bad intent set:

- Default behavior can remain append/import.
- Add an explicit **Replace active intent set** action or toggle.
- Replace must retire current active intents, then insert the new JSON intents.
- Do not hard-delete old query rows.
- This preserves historical runs and lets the existing query-set signature mark a trend break on the next tracker run.

Replacement should only apply to active `queries` for that client. Retired queries remain retired.

Suggested API shape for `POST /api/admin/queries/[clientId]`:

```ts
{
  intents: [...],
  mode?: "append" | "replace_active"
}
```

When `mode === "replace_active"`:

1. Validate all incoming intents first.
2. Retire existing active query rows for the client.
3. Insert the new intent rows.
4. Return the inserted rows.

If insertion fails after retiring, the API should return a clear error. A transactional RPC would be ideal, but for this lightweight pass the minimum requirement is validate-before-retire so common input mistakes do not wipe the active set.

## Prompt Generation Rules

Update `docs/superpowers/references/intent-generation-rules.md` so the model produces the two signals cleanly.

### Output Counts

Default target:

- **5-6 Product Visibility intents**
- **3-4 Content Authority intents**
- **5 paraphrases per intent**

This yields approximately:

```txt
9 intents x 6 wordings x 4 engines = 216 calls
```

That cost is acceptable for v1 and avoids the larger 20-40 prompt set used by broader enterprise tools.

### Output Buckets

The prompt must tell the model to use internal bucket values:

- Product Visibility -> `"bucket": "consideration"`
- Content Authority -> `"bucket": "awareness"`

The model must not output `"product_visibility"` or `"content_authority"` because the DB does not accept those values.

### Product Visibility Intent Rules

Product Visibility prompts should ask for tools, products, platforms, templates, resources, calculators, or services where a recommendation/list is natural.

Good examples:

- `best budgeting app for medical students`
- `financial planning tools for Canadian medical students`
- `medical student budget template Canada`
- `debt repayment calculator for medical school loans`

Bad examples:

- `how much debt does the average Canadian medical student graduate with`
- `how to budget as a medical student`
- `tax tips for residents`

Those are Content Authority, not Product Visibility.

### Content Authority Intent Rules

Content Authority prompts should ask educational/how-to questions that the client has content for or should plausibly own.

Good examples:

- `how to budget as a medical student in Canada`
- `how to manage a medical student line of credit`
- `how do residents plan debt repayment`
- `what expenses should medical students budget for`

Bad examples:

- broad prompts unrelated to the client's actual content strategy
- highly generic topics the client cannot credibly answer
- tax/legal/accounting topics unless the client has content and wants that lane

### Grounding Requirements

The model prompt should include:

- Client website URL
- One-line product/category description
- Brand name and variations to exclude from unbranded prompts
- Competitors for market context, not for prompt names
- GSC top queries where available
- Optional "must own / avoid" topics supplied by the operator

The model should be instructed to drop any intent that is not grounded in the website, GSC searches, or clearly relevant buyer behavior.

### Review Checklist

Before importing:

- Product Visibility prompts are product/tool/resource-selection questions.
- Content Authority prompts are educational/how-to questions.
- No client or competitor brand names appear in prompt text or paraphrases.
- Every intent has exactly one meaning; paraphrases do not drift.
- Budget/client-specific off-topic prompts are removed.
- JSON uses only `awareness`, `consideration`, or `branded`.

## Frontend Taste Constraints

This is a dashboard polish pass, not a redesign.

Use the existing dark editorial system:

- Existing serif/mono hierarchy.
- Existing thin borders and compact grid structure.
- No new cards-inside-cards.
- No marketing explanatory panels.
- Labels should be short and operational.
- Import textarea should be visible and functional, not decorative.

The Add Client modal should stay a focused operational panel. The JSON textarea can be larger than tag inputs, but the modal should not become a wizard unless future onboarding complexity demands it.

## Non-Goals

- No bucket enum migration.
- No schema migration.
- No backend scoring formula rewrite.
- No automated prompt generation inside the app.
- No brand-specific monitoring.
- No same-intents-only trend calculation.
- No redesign of the JSON importer into a full generation tool.

## Acceptance Criteria

- Product Visibility is the universal visible label for `consideration`.
- Content Authority is the universal visible label for `awareness`.
- The main dashboard score uses `bucket_scores.consideration.mention_rate`.
- Content Authority displays mention and citation signals from `bucket_scores.awareness`.
- The merged non-branded score is not presented as the main client-facing score.
- Add Client supports optional generated intent JSON with paraphrases.
- Client creation can insert full intent rows with paraphrases.
- Config import supports replacing the active intent set by retiring old active queries and inserting the new set.
- Prompt rules produce 5-6 Product Visibility intents and 3-4 Content Authority intents using existing internal bucket values.
- Branded remains visible only as `Branded - Deferred`.

## Open Implementation Notes

- Existing dirty local edits already touch some relevant files (`docs/superpowers/references/intent-generation-rules.md`, layout/overview/run detail). Implementation must review those carefully and preserve user changes where intentional.
- The replacement import should be tested against invalid JSON and invalid paraphrases before retiring active intents.
- Dashboard pages that currently use `non_branded_mention_rate` need a pass to decide whether they should switch to Product Visibility or become internal-only.
