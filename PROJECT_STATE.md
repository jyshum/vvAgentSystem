# VV Agent System — Project State

## What This Is
GEO (Generative Engine Optimization) tracking platform for Victory Velocity agency. Measures how often client brands appear in AI search responses across ChatGPT, Perplexity, Claude, and Gemini.

## Components

### Tracker (`agents/`)
Python CLI that queries 4 LLM engines with client-defined queries, detects brand mentions/citations, scores competitors, outputs CSV/JSON/HTML, optionally uploads to Supabase.

Run: `cd agents && .venv/bin/python run.py ../clients/childspot.json --upload`

### Dashboard (`dashboard/`)
Next.js 16 + Tailwind v4 + Supabase. Deployed on Vercel at `dashboard-bice-two-ikwc6u6ndz.vercel.app`.

- **Admin** (`/admin`): client list, client detail, invite users, create reports, two-pane report editor
- **Client** (`/dashboard`): visibility overview, trend chart, report list, report view with print-to-PDF
- **Auth**: magic link, invite-only, role-based routing

### Client Configs (`clients/`)
JSON files per client with brand info, target queries, competitors, `supabase_client_id`.

## Infrastructure

| Service | Details |
|---------|---------|
| Supabase | Project `vv-dashboard` (ref: `nihunlzmqcyqiacnkyxm`, US West) |
| Vercel | Project `dashboard` under `jyshums-projects` |
| DNS | Pending: `app.victoryvelocity.ca` CNAME → `cname.vercel-dns.com` |

## Live Clients

| Client | Supabase ID | Queries | Latest Run |
|--------|-------------|---------|------------|
| ChildSpot | `302eb603-3a0c-4429-bd8e-191ac30a965a` | 8 (3 generic, 3 angle, 2 operator) | 2026-06-17 — 16% mention, 0% citation |

## Key Files
- Schema: `supabase/migrations/001_initial_schema.sql`
- Tracker entry: `agents/run.py`
- Upload module: `agents/src/upload.py`
- Dashboard env: `dashboard/.env.local`
- Tracker env: `agents/.env`

## Remaining
- DNS setup (co-founder adds CNAME)
- Vercel custom domain (`vercel domains add app.victoryvelocity.ca`)
- Auto-scheduling tracker runs (deferred)
- Server-side PDF generation (deferred)
- GSC integration (deferred)
