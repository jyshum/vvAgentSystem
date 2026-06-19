# ChildSpot Dashboard Data Setup

## Goal

Set up ChildSpot as the first live client in the VV dashboard. Update the client config with revised target queries based on ChildSpot's actual value proposition, create the Supabase client record, run a fresh tracker sweep with the new queries, and upload results to Supabase so the dashboard displays real data.

## Background

ChildSpot is a two-sided real-time daycare booking marketplace (not a directory/registry). Their core differentiator is immediate availability and instant booking — no waitlists, no phone calls. They serve both parents (demand) and daycare operators (supply) in Ontario. The original 5 target queries were too generic and missed ChildSpot's angle as a connector, not a registry. They also ignored the operator side entirely.

## What Changes

### 1. Updated `clients/childspot.json`

**New target queries (8 total, 3 funnels):**

Generic top-of-funnel (parents broadly searching):
- `find daycare near me Ontario`
- `licensed daycare options in Ontario`
- `best way to find childcare in Ontario`

ChildSpot-angle (immediate connection, anti-waitlist):
- `daycare with immediate availability Ontario`
- `book daycare online without waitlist Ontario`
- `CWELCC daycare spots available Ontario`

Operator supply-side:
- `how to fill empty daycare spots Ontario`
- `attract more families to my daycare centre`

**Updated competitors:**
- Wee Watch
- KinderPage
- Daycare Radar
- Care.com
- HiMama
- OneList Ontario
- KinderSurf (replaces RateYourDaycare — KinderSurf is a direct "find and book" competitor)

**Updated brand variations:**
- ChildSpot
- Child Spot
- childspotapp.com
- childspotapp

**Populate `supabase_client_id`** after creating the Supabase row.

### 2. Create Supabase Client Row

Insert into `public.clients`:
- `name`: ChildSpot
- `brand_name`: ChildSpot
- `website_domain`: childspotapp.com
- `brand_variations`: the 4 variations above
- `target_queries`: the 8 queries above
- `competitors`: the 7 competitors above

### 3. Run Tracker With Upload

Run `python run.py ../clients/childspot.json --upload` from the `agents/` directory. This will:
- Query all 8 new queries across 4 engines (ChatGPT, Perplexity, Claude, Gemini)
- Produce 32 results (8 queries x 4 engines)
- Auto-upload to Supabase via the `--upload` flag using the `supabase_client_id` from the config

### 4. Old Runs

The 5 existing output files in `output/` stay as local archives. They are NOT uploaded to Supabase — the dashboard will only show data from the new queries.

## What Doesn't Change

- No dashboard code changes needed
- No schema changes
- No upload module changes
- Tracker code unchanged — just new input data

## Execution Order

1. Update `clients/childspot.json` (queries, competitors, brand variations)
2. Insert client row into Supabase, get UUID
3. Write UUID back into `clients/childspot.json` as `supabase_client_id`
4. Run tracker with `--upload`
5. Verify data appears in dashboard
