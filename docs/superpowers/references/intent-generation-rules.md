# Intent + Paraphrase Generation Rules

This is the manual, off-platform step for onboarding a client onto the intent-based
tracker. Run it in a ChatGPT/Claude chat, review the output, and import the JSON into
the dashboard. Do not run this inside the tracker pipeline.

Run this once per client at onboarding, and again only when deliberately refreshing the
intent set. A refresh changes the tracked query set and should be treated as a trend
break.

---

## What You're Producing

You are producing unbranded buyer intents with paraphrases:

- **Intent:** the canonical question or request a buyer would ask.
- **Paraphrases:** five natural rewordings of the same intent.
- **Bucket:** the internal dashboard bucket used for import and scoring.

Every prompt must be unbranded. The client's brand, competitors, and named products must
not appear in `prompt_text` or any paraphrase. Brand names prime the model and distort
visibility measurement.

Use the visible labels when thinking and reviewing, but output only the internal bucket
values:

| Visible label | Internal JSON `bucket` | Target count | What it tracks |
| --- | --- | ---: | --- |
| Product Visibility | `consideration` | 5-6 intents | Product, tool, template, platform, service, and shortlist-selection prompts |
| Content Authority | `awareness` | 3-4 intents | Educational, how-to, definition, planning, and expert-guidance prompts |
| Branded - Deferred | `branded` | 0 intents | Deferred; do not generate for current runs |

The model must never output `product_visibility` or `content_authority` as bucket values.
Those are visible labels only. The dashboard import expects `consideration` and
`awareness`.

Do not generate branded prompts for current runs. Branded tracking is deferred and should
only be documented as `Branded - Deferred`, not included in generated JSON.

---

## Expected Size and Cost

Default target:

- 5-6 Product Visibility intents using internal bucket `consideration`.
- 3-4 Content Authority intents using internal bucket `awareness`.
- 5 paraphrases per intent.

This usually produces about 9 intents total. Each intent has one canonical `prompt_text`
plus 5 paraphrases, so the tracker will run about:

`9 intents x 6 wordings x 4 engines = 216 calls`

Keep the set focused. More prompts increase cost and review burden without necessarily
improving signal quality.

---

## Inputs You Paste Into the Chat

Gather these before running the prompt:

1. **Client website URL** and a one-line description of what they do.
2. **Brand name** and brand variations, so the model knows what to exclude.
3. **Competitors**, for category context only. Competitor names must not appear in output.
4. **Google Search Console top queries**, exported from the client's property. These are
   real searches and should anchor the generated set. If GSC is not connected yet, say so
   and plan to revisit the intent set once query data exists.
5. **Cost sensitivity**, if the client or run budget requires a smaller set. In that case,
   prefer 5 Product Visibility and 3 Content Authority intents.

---

## Paste-Ready Prompt

```text
You are helping build an AI visibility tracking set for a company. I will give you a
company, competitors, and real Google Search Console queries. Produce unbranded buyer
INTENTS with natural PARAPHRASES.

COMPANY: <brand name> - <one-line description>
WEBSITE: <url>
COMPETITORS: <comma-separated competitor names>
REAL SEARCHES (Google Search Console top queries):
<paste the GSC query list>
COST SENSITIVITY: <standard set, or smaller set if budget-sensitive>

Return only a JSON array. Each object must use exactly this shape:
{
  "prompt_text": "<canonical natural buyer prompt>",
  "bucket": "consideration" | "awareness",
  "paraphrases": [
    "<same intent, different wording>",
    "<same intent, different wording>",
    "<same intent, different wording>",
    "<same intent, different wording>",
    "<same intent, different wording>"
  ]
}

Rules:

1. Use visible labels for reasoning, but output only internal bucket values:
   - Product Visibility = "consideration"
   - Content Authority = "awareness"
   Do not output "product_visibility" or "content_authority".

2. Generate 5-6 Product Visibility intents using bucket "consideration".
   These should be category-level product, tool, platform, template, service, or shortlist
   prompts a buyer would ask when looking for options.

3. Generate 3-4 Content Authority intents using bucket "awareness".
   These should be educational, how-to, definition, planning, checklist, or expert-guidance
   prompts that are directly relevant to the company's category and buyer.

4. Generate exactly 5 paraphrases per intent. Each paraphrase must preserve the same
   intent. Vary natural phrasing, specificity, question vs. command form, and synonyms,
   but do not drift into a different topic.

5. Every prompt must be unbranded. Do not include the company name, competitor names, or
   named products in prompt_text or paraphrases. The competitor list is context only.

6. Branded prompts are deferred. Do not generate bucket "branded" and do not create
   prompts such as "<company> reviews", "<company> pricing", "<company> alternatives",
   or "<company> vs <competitor>".

7. Ground the set in the website, GSC searches, and the category. Do not invent unrelated
   generic topics just because they are broadly popular.

8. Write like a real buyer typing into ChatGPT or Google. Use plain language. Avoid
   marketing copy, keyword stuffing, and generic LLM phrases.

9. Keep cost in mind. The default set should be about 9 intents total, producing roughly
   216 tracker calls across 4 engines. If the input says budget-sensitive, use 5 Product
   Visibility intents and 3 Content Authority intents.

Return only the JSON array, with no commentary.
```

---

## Good and Bad Examples

For a BudgetYourMD-style company that helps medical students manage finances, debt, and
budgeting during school, stay inside the medical-student finance category.

Good Product Visibility examples, bucket `consideration`:

```json
[
  {
    "prompt_text": "best budgeting tools for medical students",
    "bucket": "consideration",
    "paraphrases": [
      "budget planner for med students",
      "apps that help medical students manage money",
      "medical school budgeting tool",
      "best finance app for med students",
      "tools for tracking expenses during medical school"
    ]
  },
  {
    "prompt_text": "student loan planning help for medical students",
    "bucket": "consideration",
    "paraphrases": [
      "tools for planning med school debt",
      "medical student loan repayment planning",
      "help comparing loan options during medical school",
      "loan strategy resources for future doctors",
      "financial planning platform for medical school loans"
    ]
  }
]
```

Good Content Authority examples, bucket `awareness`:

```json
[
  {
    "prompt_text": "how should medical students budget during school",
    "bucket": "awareness",
    "paraphrases": [
      "how to manage money in medical school",
      "medical student budgeting advice",
      "what should a med student budget include",
      "how much should medical students spend each month",
      "tips for staying on budget during med school"
    ]
  },
  {
    "prompt_text": "how does medical school debt affect residency finances",
    "bucket": "awareness",
    "paraphrases": [
      "what happens to med school loans during residency",
      "how to think about medical school debt before residency",
      "financial planning for residency after med school",
      "how residency income changes student loan planning",
      "medical school debt basics for future residents"
    ]
  }
]
```

Bad examples:

- `"best stock trading apps"` - off-topic generic finance prompt; not specific to medical
  students or medical-school finances.
- `"how to start investing in crypto"` - broad consumer finance topic with no category
  grounding.
- `"BudgetYourMD pricing"` - branded prompt; branded is deferred.
- `"BudgetYourMD vs White Coat Investor"` - branded comparison; do not generate.
- `"best credit cards for everyone"` - too broad and likely to produce generic personal
  finance answers.
- `"what is compound interest"` - generic education prompt unless GSC and the website
  clearly show this exact category need.

---

## Review Checklist Before Import

Spend a few minutes reviewing the JSON before importing it:

- **JSON shape is clean:** each object has only `prompt_text`, `bucket`, and
  `paraphrases`.
- **Buckets are import-compatible:** Product Visibility uses `consideration`; Content
  Authority uses `awareness`; there is no `product_visibility`, `content_authority`, or
  `branded` output.
- **Counts are right:** 5-6 Product Visibility intents, 3-4 Content Authority intents,
  and exactly 5 paraphrases per intent.
- **No brand names:** no client brand, competitor brand, or named product appears in any
  prompt.
- **Content Authority is on-topic:** educational prompts must still connect to the
  client's category and buyer. Remove generic finance, generic marketing, generic HR, or
  other broad advice prompts that are not grounded in the category.
- **Product Visibility is category-level:** prompts ask for tools, services, resources,
  platforms, templates, or shortlist help without naming brands.
- **Paraphrases preserve intent:** rewordings do not introduce new features, audiences, or
  topics.
- **Cost is acceptable:** the set is close to the expected call volume and not padded with
  low-value prompts.

Edit freely before import. The generated JSON is a draft; the reviewed intent set is the
source of truth.
