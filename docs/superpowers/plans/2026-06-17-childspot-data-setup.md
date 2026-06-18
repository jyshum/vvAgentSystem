# ChildSpot Data Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up ChildSpot as the first live client in the VV dashboard with revised queries, Supabase data, and a fresh tracker run.

**Architecture:** No code changes — this is a data setup task. Update the client config JSON, insert a row into Supabase via CLI, backfill the UUID, run the existing tracker with `--upload`, and verify the dashboard shows data.

**Tech Stack:** Supabase CLI (`npx supabase`), Python tracker (`agents/run.py`), JSON config

---

### Task 1: Update Client Config

**Files:**
- Modify: `clients/childspot.json`

- [ ] **Step 1: Replace the contents of `clients/childspot.json`**

```json
{
  "client_name": "ChildSpot",
  "brand_name": "ChildSpot",
  "brand_variations": ["ChildSpot", "Child Spot", "childspotapp.com", "childspotapp"],
  "website_domain": "childspotapp.com",
  "supabase_client_id": "",
  "target_queries": [
    "find daycare near me Ontario",
    "licensed daycare options in Ontario",
    "best way to find childcare in Ontario",
    "daycare with immediate availability Ontario",
    "book daycare online without waitlist Ontario",
    "CWELCC daycare spots available Ontario",
    "how to fill empty daycare spots Ontario",
    "attract more families to my daycare centre"
  ],
  "competitors": [
    "Wee Watch",
    "KinderPage",
    "Daycare Radar",
    "Care.com",
    "HiMama",
    "OneList Ontario",
    "KinderSurf"
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add clients/childspot.json
git commit -m "chore: update ChildSpot config with revised queries and competitors"
```

---

### Task 2: Create Supabase Client Row

**Files:**
- Modify: `clients/childspot.json` (backfill UUID)

- [ ] **Step 1: Insert the client row into Supabase**

Run from the project root:

```bash
SUPABASE_ACCESS_TOKEN="<SUPABASE_ACCESS_TOKEN_REDACTED>" npx supabase db query --linked "\
INSERT INTO public.clients (name, brand_name, website_domain, brand_variations, target_queries, competitors) \
VALUES ( \
  'ChildSpot', \
  'ChildSpot', \
  'childspotapp.com', \
  '[\"ChildSpot\", \"Child Spot\", \"childspotapp.com\", \"childspotapp\"]'::jsonb, \
  '[\"find daycare near me Ontario\", \"licensed daycare options in Ontario\", \"best way to find childcare in Ontario\", \"daycare with immediate availability Ontario\", \"book daycare online without waitlist Ontario\", \"CWELCC daycare spots available Ontario\", \"how to fill empty daycare spots Ontario\", \"attract more families to my daycare centre\"]'::jsonb, \
  '[\"Wee Watch\", \"KinderPage\", \"Daycare Radar\", \"Care.com\", \"HiMama\", \"OneList Ontario\", \"KinderSurf\"]'::jsonb \
) RETURNING id;"
```

Expected: Returns a UUID like `"id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`

- [ ] **Step 2: Copy the returned UUID and set it in `clients/childspot.json`**

Set the `"supabase_client_id"` field to the UUID returned in Step 1.

- [ ] **Step 3: Verify the row exists**

```bash
SUPABASE_ACCESS_TOKEN="<SUPABASE_ACCESS_TOKEN_REDACTED>" npx supabase db query --linked "SELECT id, name, brand_name FROM public.clients;"
```

Expected: One row — ChildSpot with the UUID from Step 1.

- [ ] **Step 4: Commit**

```bash
git add clients/childspot.json
git commit -m "chore: backfill ChildSpot supabase_client_id"
```

---

### Task 3: Run Tracker With Upload

**Files:**
- No files modified — this produces output files and Supabase data

- [ ] **Step 1: Run the tracker**

From the `agents/` directory:

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python run.py ../clients/childspot.json --upload
```

Expected output:
- 8 queries x 4 engines = 32 results
- Local output files written to `../output/childspot_jun-17-2026_*.{csv,json,html}`
- Upload confirmation: `Uploaded to Supabase: run <run_id> (32 results)`

This will take several minutes as it queries ChatGPT, Perplexity, Claude, and Gemini sequentially.

- [ ] **Step 2: Verify Supabase data**

```bash
SUPABASE_ACCESS_TOKEN="<SUPABASE_ACCESS_TOKEN_REDACTED>" npx supabase db query --linked "SELECT r.id, r.ran_at, r.aggregate_mention_rate, r.aggregate_citation_rate, (SELECT count(*) FROM public.tracker_results tr WHERE tr.run_id = r.id) as result_count FROM public.tracker_runs r;"
```

Expected: One run with `result_count` of 32.

---

### Task 4: Verify Dashboard

- [ ] **Step 1: Open the dashboard in a browser**

Go to: `https://dashboard-bice-two-ikwc6u6ndz.vercel.app`

Log in as admin (`jaredshum101@gmail.com`).

- [ ] **Step 2: Check admin view**

Navigate to `/admin`. Verify:
- ChildSpot appears in the client list
- Clicking ChildSpot shows the client detail page with the tracker run data
- Visibility scores, competitor data, and per-query results are populated

- [ ] **Step 3: Report any issues**

If the dashboard shows empty state or errors, check:
- Browser console for Supabase errors
- That the `supabase_client_id` in the JSON matches the `id` in `public.clients`
- That `tracker_runs.client_id` matches the client row's `id`
