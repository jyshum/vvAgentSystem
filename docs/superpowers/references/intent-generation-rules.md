# Intent + Paraphrase Generation — Rules & Prompt

This is the manual, off-platform step for onboarding a client onto the intent-based
tracker. You run it in a ChatGPT/Claude chat (not in the pipeline), review the output,
and paste it into the client's Config → Queries in the dashboard.

You do this **once per client at onboarding**, and again only when you deliberately
refresh their intent set (which flags a trend break — see the drift signal).

---

## What you're producing

A set of **intents** — the buyer questions we track this client against — each with a
list of **paraphrases** (natural rewordings of the same question). The tracker fires all
the paraphrases and measures how often the brand shows up. We measure *phrasing coverage*,
not one lucky sentence, because how a question is worded changes the answer more than
re-asking the same words does.

Two buckets only:

- **awareness** — category / problem-level questions where **no brand is named**. The
  buyer is discovering options. *"best daycare management software", "how do I run a childcare center"*.
- **consideration** — shortlisting and evaluation, including comparisons. May name a
  category with qualifiers, or compare named products. *"best daycare app for a small center",
  "Brightwheel vs KinderCare", "is X good for after-school programs"*.

**Do NOT generate `branded` intents** — questions about the client's own brand
("Brightwheel reviews", "is Brightwheel worth it"). Those are recall, not visibility, and
we don't track them.

---

## Inputs you paste into the chat

Gather these before running the prompt:

1. **Client website URL** and a one-line description of what they do.
2. **Brand name** + any brand variations.
3. **Named competitors** (for comparison-style consideration intents).
4. **GSC top queries** — export the client's top Search Console queries. These are *real
   human searches* and are the anchor for grounding; do not skip them.

---

## The prompt (paste this, with the inputs filled in)

```
You are helping build an AI-visibility tracking set for a company. I will give you a
company, its competitors, and a list of REAL search queries people used to find it
(from Google Search Console). Produce the buyer INTENTS we should track this company
against, each with natural PARAPHRASES.

COMPANY: <brand name> — <one-line description>
WEBSITE: <url>
COMPETITORS: <comma-separated>
REAL SEARCHES (Google Search Console top queries):
<paste the GSC query list>

Produce a JSON array. Each element is one intent:
{
  "prompt_text": "<the canonical, most natural phrasing of the intent>",
  "bucket": "awareness" | "consideration",
  "paraphrases": ["<8 diverse natural rewordings of the SAME intent>", ...]
}

RULES — follow all of them:

1. GROUND EVERYTHING in the real searches, the company's category, and its competitors.
   Do not invent demand that isn't reflected in how people actually search or shop for
   this category. If a candidate intent isn't supported by the inputs, drop it.

2. TWO BUCKETS ONLY:
   - awareness = category/problem questions with NO brand named ("best X", "how to Y").
   - consideration = shortlisting/evaluation, including comparisons ("best X for Y",
     "A vs B", "alternatives to A", "is A good for Y").
   Classify each intent into exactly one.

3. NEVER produce a branded intent — nothing that names the COMPANY itself as the subject
   ("<brand> reviews", "is <brand> good", "<brand> pricing"). We do not track these.
   (Comparisons that name the company against a competitor ARE allowed and go in
   consideration — "<brand> vs <competitor>".)

4. PARAPHRASES must preserve the intent exactly — same question, different surface form.
   Vary them the way real people vary: question vs. command vs. keyword phrase; formal vs.
   casual; more vs. less specific; synonyms; with and without qualifiers. Give ~8 per
   intent. Do NOT drift the meaning, and do NOT just reorder words.

5. Write like a real buyer typing into ChatGPT or Google — natural, plain language. No
   marketing voice, no LLM-ese ("elevate", "seamless", "in today's landscape"), no keyword
   stuffing.

6. Aim for roughly 6–12 intents total, weighted toward how people actually search. Quality
   and realism over quantity.

Return ONLY the JSON array, nothing else.
```

---

## Reviewing the output before you paste it

Spend two minutes checking:

- **No branded intents** slipped in (nothing about the client's own brand as the subject).
- **Buckets are right** — awareness has no brand named; comparisons are in consideration.
- **Paraphrases are genuinely different wordings**, not near-duplicates, and none has
  drifted to a different question.
- **Everything traces to a real search or an obvious category question** — cut anything
  that feels invented.
- **It reads like a human**, not marketing copy.

Edit freely — you're the gate. Then paste the JSON into the client's Config → Queries
(bulk import), which stores each intent with its bucket and paraphrases.

---

## Why it's manual (and stays manual)

Generating intents is an occasional onboarding task, not something that runs every cycle,
so it doesn't belong in the pipeline. Using an LLM for the *paraphrases* is standard and
low-risk (the intent is fixed; you're only varying wording). Using an LLM for the *seed
intents* is only safe because it's grounded in the client's real GSC searches and gated by
your review — that's what keeps it from inventing prompts the brand happens to look good on.
