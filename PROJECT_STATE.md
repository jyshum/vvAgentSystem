# VV Agent System — Project State

## Active Development — Deterministic Technical Audit Foundation

- **Branch:** `feature/deterministic-technical-audit`
- **Rollout:** development only; default off with `TECHNICAL_AUDIT_V1_ENABLED=false`
- **Database:** additive migration `supabase/migrations/014_technical_audit_foundation.sql`; not applied to production by this branch
- **Implemented slice:** immutable five-status audit contract, bounded evidence observations, versioned registry, deterministic `llms.txt`/title/description/canonical checks, persisted runs/results, and no-score run checklist
- **Safety boundary:** when enabled, legacy structural scoring and AI-generated technical cards are skipped; the new findings cannot create or publish remediation
- **Agent verification:** `cd agents && .venv/bin/python -m pytest -q`
- **Dashboard verification:** `cd dashboard && npm test && npm run build`
- **Operator guide:** `docs/technical-audit-operations.md`

The approved remaining sections and remediation adapters are sequenced in `docs/superpowers/plans/2026-07-14-technical-audit-foundation.md`. Historical readiness scores remain readable as legacy data.

## What This Is
GEO (Generative Engine Optimization) platform for Victory Velocity agency. Tracks how often client brands appear in AI responses, audits client websites for GEO health, and generates actionable fixes.

---

## Where Things Live

| Layer | Status | URL / Location |
|-------|--------|----------------|
| Dashboard (Next.js) | Live | `dashboard-bice-two-ikwc6u6ndz.vercel.app` |
| Custom domain | Pending DNS | `app.victoryvelocity.ca` → CNAME → `cname.vercel-dns.com` |
| Supabase | Live | Project `vv-dashboard` (ref: `nihunlzmqcyqiacnkyxm`, US West) |
| Python agents | Local only | Run manually from `agents/` |

---

## Components

### AI Visibility Tracker
Queries ChatGPT, Perplexity, Claude, and Gemini with client target queries. Detects brand mentions and citations. Results saved to Supabase and viewable in dashboard.

`python run.py --client-id <uuid> --upload`

### GEO Audit System *(branch: feat/audit-recommendation-engine — not yet merged)*
Crawls a client's website, scores each page against 6 GEO pillars (Content Structure, Fact Density, Source Citations, Authority Signals, Schema Markup, Freshness). Uses page-type classification so only relevant pillars apply per page. Generates before/after action cards for weak pages. Can open GitHub PRs with fixes.

```
python audit.py --client-id <uuid> --upload
python recommend.py --run-id <uuid> --upload
python implement.py --card-id <uuid>
```

**Requires:** Run `supabase/migrations/002_audit_schema.sql` in Supabase SQL Editor before using.

### Reddit Scout *(same branch)*
Surfaces Reddit posts where the client brand should be mentioned but isn't. Uses public `.json` endpoints — no API key required.

`python scout.py --client-id <uuid> --upload`

---

## Live Clients

| Client | Supabase ID | Latest Tracker Run |
|--------|-------------|--------------------|
| ChildSpot | `302eb603-3a0c-4429-bd8e-191ac30a965a` | 2026-06-17 — 16% mention, 0% citation |

---

## Key Files

| File | Purpose |
|------|---------|
| `supabase/migrations/001_initial_schema.sql` | Tracker tables |
| `supabase/migrations/002_audit_schema.sql` | Audit tables (run manually) |
| `agents/run.py` | Tracker CLI |
| `agents/audit.py` | Audit CLI |
| `agents/recommend.py` | Recommendation engine CLI |
| `agents/implement.py` | Implementation handler CLI |
| `agents/scout.py` | Reddit scout CLI |
| `clients/childspot.json` | ChildSpot config |
| `agents/.env` | ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY |
| `dashboard/.env.local` | Supabase keys for Next.js |

---

## Deferred

- Auto-scheduling tracker and audit runs
- Server-side PDF generation
- GSC integration
- WordPress implementation handler (copy-paste fallback used until a WP client onboards)
- Webflow implementation handler
