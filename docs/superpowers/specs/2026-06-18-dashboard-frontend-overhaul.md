# Dashboard Frontend Overhaul
**Date:** 2026-06-18  
**Status:** Approved for implementation  
**Scope:** Admin-only. No client portal, no user management, no invite system.

---

## Overview

Replace the current brainstorm HTML mockup with a production Next.js 15 dashboard that lets Victory Velocity admins manage GEO clients, trigger tracker runs via Railway, and write/publish weekly reports. Supabase handles auth and all data. Railway hosts and executes the Python tracker.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 15 (App Router) |
| Styling | Tailwind CSS |
| Animation | Framer Motion |
| Auth + DB | Supabase |
| Tracker hosting | Railway |
| Fonts | Cormorant Garamond, Newsreader, IBM Plex Mono, Schibsted Grotesk |

---

## Routes

```
/                           → redirect to /clients
/clients                    → client list
/clients/[id]/config        → config editor
/clients/[id]/runs          → runs list
/clients/[id]/runs/[runId]  → run detail
/clients/[id]/reports       → reports list
/clients/[id]/reports/[reportId]       → report editor
/clients/[id]/reports/[reportId]/view  → read-only PDF view
```

All routes are protected. Unauthenticated requests redirect to `/login`. Single admin account via Supabase auth (email/password).

---

## Pages

### /clients
- Agency-level stats strip: active clients, avg mention rate, avg citation rate, reports this month
- Table: client name, domain, mention rate (latest run), citation rate (latest run), last run date + freshness pill, latest published report link
- "+ ADD CLIENT" opens a modal with name, domain, brand name fields (creates row in `clients` table)
- Row click → `/clients/[id]/runs` (default tab)

### /clients/[id] — shared chrome
- Sticky sub-nav with three tabs: CONFIG / RUNS / REPORTS
- Client name + domain in header

### /clients/[id]/config
Fields map 1:1 to the `clients` Supabase table:
- Brand name
- Website domain
- Brand variations (tag input, stored as jsonb array)
- Target queries (tag input, stored as jsonb array)
- Competitors (tag input, stored as jsonb array)
- Save button → upserts to Supabase

**Note:** Saving config does not automatically trigger a run. Admin manually triggers from the RUNS tab.

### /clients/[id]/runs
- "RUN TRACKER" button → triggers Railway job (see Infrastructure section)
- Table of past runs: date, mention rate, citation rate, queries run, status badge, "→ VIEW" and "→ MAKE REPORT" actions
- Row click → `/clients/[id]/runs/[runId]`

### /clients/[id]/runs/[runId] — Run Detail
Sections (matching approved mockup):
1. **Header**: date, run metadata, "→ MAKE REPORT" button
2. **KPI strip**: mention rate, citation rate, top competitor, citations found
3. **Per-engine breakdown**: 4 cards (ChatGPT, Perplexity, Claude, Gemini) — stacked bar + cited/mentioned/not-found counts
4. **Competitor SoV**: table with horizontal bars
5. **Citation URLs discovered**: list of URLs, which engines cited them
6. **Query results**: 8×4 overview matrix (click row to jump) + detailed query blocks (first 3 visible, "SHOW MORE" expands remaining 5) — each engine row shows real AI excerpt where brand was mentioned

Data source: `tracker_runs` (aggregate) + `tracker_results` (per query×engine).

### /clients/[id]/reports
- "→ MAKE REPORT" on a run row pre-populates a new report draft with that run's KPI data
- "+ NEW BLANK REPORT" creates a report with no associated run (for manual/custom reports)
- Table: week, status (draft/published), associated run, actions (edit, view, delete)

### /clients/[id]/reports/[reportId] — Report Editor
Split-pane: left = form fields, right = live paper preview.

Editable fields (map to `reports` table):
- `exec_summary` (textarea)
- `highlights` (jsonb — list of strings)
- `work_completed` (jsonb — list of strings)
- `priorities` (jsonb — ordered list of strings)
- `blockers` (jsonb — list of strings)
- `search_console` (jsonb — impressions, clicks, ctr, position)

KPI section (mention rate, citation rate) auto-populated from associated `run_id` if set; editable if no run linked.

Actions: SAVE DRAFT / PUBLISH REPORT

### /clients/[id]/reports/[reportId]/view — Report PDF View
Clean paper document. Sections: header, exec summary, AI visibility KPIs, highlights, work completed, priorities, blockers, GSC. "PRINT / PDF →" triggers browser print. "EDIT" navigates to editor.

---

## Infrastructure: Tracker ↔ Dashboard

**Current gap:** `agents/run.py` reads config from a local JSON file. The dashboard writes config to Supabase. These are disconnected.

**Fix — update `agents/run.py`:**
```
# New flag
python run.py --client-id <supabase_uuid>

# Existing flag still works for local dev
python run.py --config clients/childspot.json
```

When `--client-id` is provided, `run.py` fetches the client row from Supabase and constructs the config dict. The `tracker.py` interface (`run_tracker(config)`) is unchanged.

After the run completes, `run.py` writes results to Supabase:
- Insert row into `tracker_runs` with aggregate scores
- Insert rows into `tracker_results` for each query×engine result

**Railway setup:**
- Railway project runs `python run.py --client-id $CLIENT_ID`
- `CLIENT_ID` passed as an environment variable per job trigger
- Dashboard triggers a run by calling the Railway API (POST `/deployments/trigger` with `CLIENT_ID` in env vars)
- Railway service has `SUPABASE_URL` and `SUPABASE_KEY` env vars set

**Dashboard trigger flow:**
1. Admin clicks "RUN TRACKER" on the RUNS page
2. Dashboard calls a Next.js API route: `POST /api/runs/trigger`
3. API route calls Railway API with `client_id` as job variable
4. Railway executes `run.py --client-id <id>`
5. Tracker fetches config from Supabase, runs, writes results back to Supabase
6. Dashboard polls (or uses Supabase realtime) for the new `tracker_runs` row to appear
7. Run row appears in the RUNS table

---

## Data Model (existing Supabase schema)

```sql
clients (id, name, brand_name, website_domain, brand_variations jsonb, target_queries jsonb, competitors jsonb)

tracker_runs (id, client_id, ran_at, aggregate_mention_rate, aggregate_citation_rate, per_engine_scores jsonb, competitor_scores jsonb)

tracker_results (id, run_id, query, engine, model, brand_mentioned, brand_cited, citation_url, competitor_mentions jsonb, response_text)

reports (id, client_id, run_id nullable, week_start, status, exec_summary, work_completed jsonb, priorities jsonb, highlights jsonb, blockers jsonb, search_console jsonb)
```

No schema migrations needed for the initial dashboard implementation.

---

## Design System

| Token | Value |
|---|---|
| Background | `#0e0e0f` |
| Foreground | `#f5f4f1` |
| Muted | `rgba(245,244,241,0.5)` |
| Faint | `rgba(245,244,241,0.3)` |
| Hair (border) | `rgba(245,244,241,0.08)` |
| Positive | `#84d8ab` |
| Negative | `#e89aa0` |
| Paper bg | `#f1ede4` |
| Paper ink | `#1a1915` |

Fonts loaded via `next/font/google`. Nav is sticky, blurs on scroll. All interactive rows use a left-indent hover (padding-left transition). Buttons invert on hover (transparent → filled).

---

## Deferred (post-MVP)

- Auto-scheduled tracker runs (cron)
- GSC integration (live data pull)
- GSC metrics on client list dashboard
- Server-side PDF generation
- Run status polling / realtime (MVP: manual refresh)
