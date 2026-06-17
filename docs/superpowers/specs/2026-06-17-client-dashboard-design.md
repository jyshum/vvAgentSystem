# VV Client Dashboard — Design Spec

## Overview

A Next.js + Tailwind CSS dashboard deployed on Vercel at `app.victoryvelocity.ca`. Supabase provides auth (magic link, invite-only) and data storage (Postgres + RLS). The tracker agent (`run.py`) pushes results to Supabase after each local run. Admin team edits and publishes weekly reports; clients log in to view their visibility dashboard and download report PDFs.

## Tech Stack

- **Frontend:** Next.js 14+ (App Router), Tailwind CSS, TypeScript
- **Backend:** Supabase (Postgres, Auth, RLS, `supabase-py` for tracker uploads)
- **Hosting:** Vercel at `app.victoryvelocity.ca`
- **PDF Export:** Browser `window.print()` with print-optimized CSS
- **Fonts:** Newsreader (serif, headings/body — from landing page), Cormorant Garamond (serif, report title/large display — from report generator), Schibsted Grotesk (sans), IBM Plex Mono (mono) — all loaded from Google Fonts
- **Auth:** Supabase magic link, invite-only (no public signup)

---

## Design System — Exact Token Reference

All tokens are pulled directly from the VV landing page (`globals.css`) and report generator (`styles.css`). The dashboard must replicate these exactly.

### Colors (from landing page `globals.css`)

```
--ink:        #0e0e0f        /* primary background */
--ink-soft:   #141416        /* card/section backgrounds */
--ink-2:      #19191c        /* elevated surfaces */
--white:      #f5f4f1        /* primary text (warm cream) */
--paper:      #f1ede4        /* light surface for report "professional" theme */
--paper-ink:  #17150f        /* dark text on light surfaces */
--mute:       rgba(245,244,241,0.58)  /* secondary text */
--faint:      rgba(245,244,241,0.36)  /* tertiary text */
--ghost:      rgba(245,244,241,0.13)  /* subtle borders/fills */
--hair:       rgba(245,244,241,0.11)  /* hairline dividers */
```

### Accent/Status Colors (from report generator `styles.css`)

```
--pos:        #1f7a52        /* positive/good — professional theme */
--neg:        #b23a3a        /* negative/bad — professional theme */
--pos-dark:   #84d8ab        /* positive — editorial/dark theme */
--neg-dark:   #e89aa0        /* negative — editorial/dark theme */
--accent:     #1e3a5f        /* accent blue — professional theme */
--accent-dark: #ffffff       /* accent — editorial theme (white) */
```

Since the dashboard is always dark (editorial theme), use:
- Good/positive: `#84d8ab`
- Bad/negative: `#e89aa0`
- Neutral accent: `#f5f4f1` (warm white)

### Typography (from landing page `layout.tsx`)

```
--serif: 'Newsreader', Georgia, serif
--sans:  'Schibsted Grotesk', system-ui, sans-serif
--mono:  'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace
```

Usage rules (from landing page + report generator patterns):
- **Dashboard headings/numbers:** Newsreader, font-weight 400, negative letter-spacing (-0.02em to -0.03em)
- **Report title (large display):** Cormorant Garamond, font-weight 300, 72px (replicating report generator `.rpt-title`)
- **UI labels/section headers:** Schibsted Grotesk or IBM Plex Mono, 11-13px, font-weight 500-600, letter-spacing 0.08-0.14em, uppercase
- **Body text:** Newsreader, 16-18px, line-height 1.6-1.7
- **Report body (editorial theme):** Cormorant Garamond (replicating report generator `--report-body: var(--serif)`)
- **Badges/tags:** IBM Plex Mono, 9-11px, letter-spacing 0.1-0.2em, uppercase
- **Italic for emphasis:** Newsreader/Cormorant italic for subtitles, quotes, query text

### Component Patterns (replicated exactly)

**Cards** — from landing page `.mk-report` and report generator `.kpi`:
```css
background: #19191c;            /* --ink-2 */
border: 1px solid rgba(245,244,241,0.11);  /* --hair */
border-radius: 12px;
box-shadow: 0 40px 90px -40px rgba(0,0,0,0.8);
overflow: hidden;
```

**Score display** — from landing page `.mk-report .score`:
```css
.score .big { font-size: 56px; font-family: var(--serif); color: var(--white); line-height: 1; }
.score .den { font-size: 26px; color: var(--faint); }
.score .lbl { font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--mute); }
```

**Section labels** — from report generator `.section-label`:
```css
font-family: var(--mono);
font-size: 12px;
letter-spacing: 0.14em;
text-transform: uppercase;
color: var(--mute);
padding-bottom: 11px;
border-bottom: 1px solid var(--hair);
```

**Status badges** — from report generator `.status-badge`:
```css
font-family: var(--mono);
font-size: 8px;
letter-spacing: 0.1em;
text-transform: uppercase;
padding: 4px 9px;
/* Variants: */
.badge-yes  { color: var(--paper); background: var(--pos); }
.badge-no   { color: var(--muted); border: 1px solid var(--hair-strong); }
.badge-part { color: var(--accent); border: 1px solid var(--accent); }
```

**CTA buttons** — from landing page `.cta`:
```css
font-family: var(--sans);
font-size: 13px;
font-weight: 600;
letter-spacing: 0.06em;
display: inline-flex;
align-items: center;
gap: 11px;
padding: 15px 26px;
border: 1px solid var(--ghost);
color: var(--white);
background: transparent;
border-radius: 2px;
transition: all 0.35s ease;
/* Solid variant: */
.cta.solid { background: var(--white); color: var(--ink); border-color: var(--white); }
.cta.solid:hover { background: transparent; color: var(--white); border-color: var(--ghost); }
```

**Nav bar** — from landing page `.nav`:
```css
height: 78px;
display: flex;
align-items: center;
justify-content: space-between;
padding: 0 56px;
background: rgba(14,14,15,0.82);
backdrop-filter: blur(12px);
border-bottom: 1px solid var(--hair);
```
Nav wordmark: Newsreader, 21px, `letter-spacing: 0.01em`
Nav links: Schibsted Grotesk, 12.5px, weight 500, `letter-spacing: 0.08em`

**Table rows** — from report generator `.rpt-spot` and landing page `.mk-report .row`:
```css
padding: 13px 0;
border-top: 1px solid var(--hair);
/* Query text: */ font-family: var(--serif); font-style: italic; font-size: 18px;
/* Engine label: */ font-family: var(--mono); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--faint);
```

**Bar/progress** — from landing page `.mk-report .pbar`:
```css
height: 3px;
background: var(--hair);
/* Fill: */ position: absolute; left: 0; top: 0; bottom: 0; background: var(--white);
```

**Form inputs** — from report generator:
```css
background: transparent;
border: 1px solid rgba(255,255,255,0.14);
color: #fff;
font-family: var(--serif);
font-size: 14px;
padding: 8px 10px;
/* Focus: */ border-color: rgba(255,255,255,0.42);
/* Placeholder: */ color: rgba(255,255,255,0.22);
```

**Textarea** — from report generator:
```css
font-style: italic;
line-height: 1.6;
min-height: 70px;
resize: vertical;
```

**Scroll reveal animation** — from landing page `.rv`:
```css
opacity: 0;
transform: translateY(22px);
transition: opacity 0.9s cubic-bezier(0.2, 0.7, 0.2, 1), transform 0.9s cubic-bezier(0.2, 0.7, 0.2, 1);
/* When visible: */ opacity: 1; transform: none;
```

---

## Auth & Security

### Magic Link Flow
1. Admin creates a client account in admin panel (enters client email)
2. Supabase sends magic link email to client
3. Client clicks link → lands on `/dashboard`
4. Session managed by Supabase Auth with `@supabase/ssr` for Next.js

### Security Measures
- **Row Level Security (RLS)** on ALL tables — clients can only SELECT rows matching their `client_users.client_id`
- **Server-side session validation** — Next.js middleware checks Supabase session on every `/admin/*` and `/dashboard/*` route; redirects to `/login` if invalid
- **Role enforcement** — `client_users.role` checked server-side; clients cannot access `/admin/*` routes
- **Invite-only** — no public signup endpoint; Supabase Auth email signups disabled; only admin-triggered invites
- **Short-lived sessions** — Supabase default JWT expiry (1 hour) with refresh tokens
- **No DELETE for clients** — RLS policies grant only SELECT on client-facing tables
- **Response text hidden from clients** — `tracker_results.response_text` is excluded from client-facing queries (only admins see raw LLM output)
- **HTTPS only** — enforced by Vercel

### Middleware Logic
```
/login          → public
/admin/*        → requires auth + role='admin'
/dashboard/*    → requires auth + role='client'
/               → redirect to /login
```

---

## Database Schema

### `clients`
| Column | Type | Constraints |
|---|---|---|
| `id` | uuid | PK, default gen_random_uuid() |
| `name` | text | NOT NULL |
| `brand_name` | text | NOT NULL |
| `website_domain` | text | |
| `brand_variations` | jsonb | DEFAULT '[]' |
| `target_queries` | jsonb | DEFAULT '[]' |
| `competitors` | jsonb | DEFAULT '[]' |
| `created_at` | timestamptz | DEFAULT now() |

### `client_users`
| Column | Type | Constraints |
|---|---|---|
| `id` | uuid | PK, default gen_random_uuid() |
| `user_id` | uuid | FK → auth.users, NOT NULL |
| `client_id` | uuid | FK → clients, NULLABLE (null for admins) |
| `role` | text | NOT NULL, CHECK (role IN ('admin', 'client')) |
| `created_at` | timestamptz | DEFAULT now() |
| | | UNIQUE(user_id) |

### `tracker_runs`
| Column | Type | Constraints |
|---|---|---|
| `id` | uuid | PK, default gen_random_uuid() |
| `client_id` | uuid | FK → clients, NOT NULL |
| `ran_at` | timestamptz | DEFAULT now() |
| `aggregate_mention_rate` | float | |
| `aggregate_citation_rate` | float | |
| `per_engine_scores` | jsonb | |
| `competitor_scores` | jsonb | |

### `tracker_results`
| Column | Type | Constraints |
|---|---|---|
| `id` | uuid | PK, default gen_random_uuid() |
| `run_id` | uuid | FK → tracker_runs, NOT NULL |
| `query` | text | NOT NULL |
| `engine` | text | NOT NULL |
| `model` | text | |
| `brand_mentioned` | boolean | DEFAULT false |
| `brand_cited` | boolean | DEFAULT false |
| `citation_url` | text | |
| `competitor_mentions` | jsonb | DEFAULT '[]' |
| `response_text` | text | |
| `queried_at` | timestamptz | DEFAULT now() |

### `reports`
| Column | Type | Constraints |
|---|---|---|
| `id` | uuid | PK, default gen_random_uuid() |
| `client_id` | uuid | FK → clients, NOT NULL |
| `run_id` | uuid | FK → tracker_runs, NULLABLE |
| `week_start` | date | NOT NULL |
| `status` | text | DEFAULT 'draft', CHECK (status IN ('draft', 'published')) |
| `exec_summary` | text | |
| `work_completed` | jsonb | DEFAULT '[]' |
| `priorities` | jsonb | DEFAULT '[]' |
| `highlights` | jsonb | DEFAULT '[]' |
| `blockers` | jsonb | DEFAULT '[]' |
| `notes` | text | |
| `search_console` | jsonb | |
| `published_at` | timestamptz | |
| `created_at` | timestamptz | DEFAULT now() |

### RLS Policies

**clients:**
- Admin: SELECT, INSERT, UPDATE, DELETE
- Client: SELECT WHERE `id IN (SELECT client_id FROM client_users WHERE user_id = auth.uid())`

**tracker_runs:**
- Admin: SELECT, INSERT
- Client: SELECT WHERE `client_id IN (SELECT client_id FROM client_users WHERE user_id = auth.uid())`

**tracker_results:**
- Admin: SELECT, INSERT (full access to all columns including `response_text`)
- Client: No direct access. Create a Postgres VIEW `tracker_results_client` that selects all columns EXCEPT `response_text`, then grant client SELECT on the view with RLS filtering by `run_id IN (SELECT id FROM tracker_runs WHERE client_id IN (SELECT client_id FROM client_users WHERE user_id = auth.uid()))`. Client-facing queries always use the view, never the raw table.

**reports:**
- Admin: SELECT, INSERT, UPDATE
- Client: SELECT WHERE `status = 'published' AND client_id IN (...)`

---

## Route Structure

| Route | Access | Purpose |
|---|---|---|
| `/login` | Public | Magic link login form |
| `/admin` | Admin | Client list with status cards |
| `/admin/clients/[id]` | Admin | Client detail: config, run history, user management |
| `/admin/reports/[id]` | Admin | Two-pane report editor with live preview |
| `/dashboard` | Client | Visibility overview + report list |
| `/dashboard/reports/[id]` | Client | Full report view with PDF export |

---

## Client Dashboard (`/dashboard`)

### Visibility Overview (top)

Four KPI cards in a grid (replicates report generator `.kpi-grid`):

1. **Overall Visibility** — aggregate mention rate as large serif number, color-coded, week-over-week delta with arrow
2. **Citation Rate** — aggregate citation rate, same treatment
3. **Engines Tracked** — count (4)
4. **Reports Available** — count of published reports

Card styling matches `.mk-report` from landing page: `background: #19191c`, `border: 1px solid var(--hair)`, `border-radius: 12px`.

Score numbers use `.score .big` pattern: Newsreader 56px.

Delta indicators use report generator `.kpi-delta` pattern: monospace 10px, green arrow up / red arrow down.

### Trend Chart (middle)

Full-width line chart showing aggregate mention rate over time.

Uses the same SVG sparkline approach as the report generator (`sparklineSVG` function) but rendered larger. Line styling: `stroke: var(--pos-dark)` (#84d8ab), area fill at 16% opacity, dot on latest point.

X-axis: week labels in monospace 9px. Y-axis: percentage.

Per-engine lines can be toggled via small engine pills below the chart (monospace, uppercase, `--ghost` border, active = `--white` text).

### Report List (bottom)

Chronological list (newest first), styled like landing page `.mk-report .row`:

Each row:
- Week range (Newsreader italic, 18px)
- Visibility score (monospace, color-coded)
- Published date (monospace 10px, `--faint`)
- "View Report →" link (Schibsted Grotesk, 12.5px)

Rows separated by `border-top: 1px solid var(--hair)`.

### Report View (`/dashboard/reports/[id]`)

Full report page replicating the report generator's "editorial" theme output. Sections:

1. **Header** — "Victory Velocity" brand mark, "GEO · Weekly Performance Report" kicker (mono 12px, uppercase), client name (Newsreader 72px), week range (italic 21px), domain + "Prepared by" (mono 10px)
2. **Executive Summary** — italic serif 22px
3. **AI Visibility Scores** — KPI grid with per-engine cards (mention rate + citation rate per engine), aggregate scores
4. **Competitor Comparison** — table with brand highlighted, sorted by mention rate
5. **GEO Query Results** — table: query (italic serif) × engine (mono) × status badge (CITED/MENTIONED/NOT FOUND)
6. **Work Completed** — checklist with check SVG icons
7. **Priorities** — numbered list (mono numbers)
8. **Highlights / Blockers** — bullet lists (em dash bullets)
9. **Notes** — italic serif
10. **Footer** — "Prepared by Victory Velocity" + week range

Print CSS: hides nav, full-width page, `@page { margin: 0 }`, `padding: 18mm`, `break-inside: avoid` on sections.

---

## Admin Panel (`/admin`)

### Client List (`/admin`)

Grid of client cards. Each card (styled like `.mk-report`):
- Client name (Newsreader 28px)
- Domain (mono 11px, `--faint`)
- Latest visibility score (large number, color-coded)
- Last run date (mono 10px)
- Report status badge: "DRAFT" (border only), "PUBLISHED" (green fill), "NO REPORT" (faint)
- Action buttons: "View" / "New Report" (`.cta` button style)

"Add Client" button at top — `.cta.solid` style.

### Client Detail (`/admin/clients/[id]`)

**Client config section:**
- Editable fields: name, brand_name, domain, brand_variations (tag input), target_queries (list), competitors (list)
- Form inputs match report generator style (transparent bg, hairline border, serif font)
- Save button (`.cta.solid`)

**User management section:**
- List of linked users (email, role)
- "Invite Client" button → enters email, triggers Supabase magic link invite

**Tracker run history:**
- Table: date (mono), aggregate scores, per-engine mini-scores, "Create Report" button
- Rows styled like report generator `.rpt-spot` table

### Report Editor (`/admin/reports/[id]`)

Two-pane layout (replicates report generator's `form-panel` + `preview-panel`):

**Left pane — Editor (420px, matches report generator `.form-panel`):**
- Section labels: mono 12px, uppercase, `letter-spacing: 0.14em`, bottom border
- Auto-populated (read-only): visibility scores from linked tracker run
- Editable fields:
  - Executive Summary (textarea, italic, placeholder: "One short paragraph...")
  - Search Console Metrics (4 metric groups: impressions, clicks, CTR, position — each with "This week" and "Baseline" inputs, matching report generator `.metric-pair` layout)
  - Highlights / Wins (add/remove list)
  - Work Completed (checklist with add/remove)
  - Next Week Priorities (numbered list)
  - Blockers / Risks (add/remove list)
  - Notes (textarea)

**Right pane — Live Preview:**
- Renders the report exactly as the client will see it
- Updates in real-time as admin types (like report generator)
- Background: `#0e0e0e` (--backdrop editorial)

**Top bar:**
- Report status badge
- "Publish" button (`.cta.solid`) / "Unpublish" button (`.cta` outline)
- "Export PDF" button

---

## Tracker Agent Integration

### Changes to `run.py`

Add a `--upload` flag (or make it default) that pushes results to Supabase after the run completes:

1. After `run_tracker()` returns `results` and `scores`
2. Create a `tracker_runs` row with scores
3. Batch-insert `tracker_results` rows with all individual results
4. Print Supabase upload confirmation

Requires: `supabase-py` added to `agents/pyproject.toml`, `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env`.

Uses the Supabase **service role key** (not anon key) since this runs locally with full write access. The service key bypasses RLS — appropriate for a server-side script.

### Changes to `clients/childspot.json`

Add a `supabase_client_id` field that maps to the `clients.id` in Supabase, so the tracker knows which client record to link to.

---

## Deferred / Post-Launch

1. **Automated tracker scheduling** — Cron job or Supabase Edge Function to run tracker weekly
2. **Server-generated PDFs** — Puppeteer/headless browser for real `.pdf` file downloads
3. **Google Search Console API integration** — Auto-pull impressions, clicks, CTR, position
4. **Search Console metrics on dashboard** — Currently report-only; add to dashboard when GSC access available
5. **Report diffing** — Show what changed between two consecutive weeks
6. **Email notifications** — Notify clients when a new report is published

---

## File Structure

```
dashboard/
├── app/
│   ├── layout.tsx              # Root layout: fonts, global styles, Supabase provider
│   ├── globals.css             # Design tokens (copied from landing page + report generator)
│   ├── login/
│   │   └── page.tsx            # Magic link login
│   ├── admin/
│   │   ├── layout.tsx          # Admin layout: nav, role check
│   │   ├── page.tsx            # Client list
│   │   ├── clients/
│   │   │   └── [id]/
│   │   │       └── page.tsx    # Client detail
│   │   └── reports/
│   │       └── [id]/
│   │           └── page.tsx    # Report editor (two-pane)
│   └── dashboard/
│       ├── layout.tsx          # Client layout: nav, session check
│       ├── page.tsx            # Visibility overview + report list
│       └── reports/
│           └── [id]/
│               └── page.tsx    # Report view + PDF export
├── components/
│   ├── ui/                     # Shared UI: Button, Card, Badge, Input, etc.
│   ├── charts/
│   │   └── SparklineChart.tsx  # SVG sparkline (port from report generator)
│   ├── report/
│   │   ├── ReportView.tsx      # Full report renderer (shared by admin preview + client view)
│   │   ├── KPIGrid.tsx         # 4-card metrics grid
│   │   ├── CompetitorTable.tsx # Competitor comparison table
│   │   ├── QueryResultsTable.tsx # Per-query per-engine results
│   │   └── ReportHeader.tsx    # Report header block
│   ├── admin/
│   │   ├── ClientCard.tsx      # Client card for admin list
│   │   ├── ReportEditor.tsx    # Left-pane editor form
│   │   └── InviteClientForm.tsx
│   └── dashboard/
│       ├── VisibilityOverview.tsx  # KPI cards for client dashboard
│       ├── TrendChart.tsx         # Full-width trend line
│       └── ReportList.tsx         # Chronological report list
├── lib/
│   ├── supabase/
│   │   ├── client.ts           # Browser Supabase client
│   │   ├── server.ts           # Server Supabase client (for RSC/middleware)
│   │   └── middleware.ts       # Auth middleware helper
│   ├── types.ts                # TypeScript types matching DB schema
│   └── utils.ts                # Score color, formatting helpers
├── middleware.ts               # Next.js middleware: auth + role routing
├── tailwind.config.ts
├── package.json
└── tsconfig.json
```
