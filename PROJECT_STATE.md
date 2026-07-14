# VV Agent System — Project State

## Active Development — Simplified Technical Audit V1

- **Rollout:** development only; `TECHNICAL_AUDIT_V1_ENABLED=true` requires `TECHNICAL_AUDIT_INTERNAL_CLIENT_IDS` to explicitly list the client. An empty allowlist enables no clients; `*` is development/testing only.
- **Check sets:** `TECHNICAL_AUDIT_CHECK_SETS=foundation`; `foundation` is the only implemented set. An unavailable set is a configuration error, not a partial audit.
- **Database:** additive migration `supabase/migrations/014_technical_audit_foundation.sql`; not applied to production.
- **Implemented V1 path:** an allowlisted run writes immutable technical observations/results for deterministic `llms.txt`/title/description/canonical checks and uses the five-status audit contract.
- **Legacy preservation:** disabled or unallowlisted clients use the legacy route. The Pages primary tab is hidden but its direct route remains available; run pages use technical or legacy presentation and preserve historical legacy evidence.
- **Manual community selection:** V1 bypasses matching, scoring, briefs, and AI fixes, then directly selects at most five manual `community_check` cards from positive tracker competitor leads.
- **Current product boundary:** V1 writes no `query_page_matches` or `page_citation_scores`, has no technical remediation cards, and cannot approve or publish a client-site change. Technical result/action composition is next.
- **Operator guide:** `docs/technical-audit-operations.md`

### Ordered follow-on roadmap

1. **Unified technical audit cards and workflow** — linked immutable result evidence plus editable workflow records; Fail/Review/Unknown inbox behavior; Pass/Not applicable audit-page behavior; grouping, lifecycle, stale-state guard, and fresh re-audit verification.
2. **Protocol check set** — robots.txt, sitemap, TLS/HTTPS, and schema integrity/coverage with bounded evidence and five-state outcomes.
3. **Site-integrity check set** — broken links, image integrity/appropriateness review boundaries, freshness consistency, and existing source-support verification with bounded crawling.
4. **Performance and connected-service check set** — CrUX, Lighthouse lab context, Google Search Console, and Bing Webmaster Tools; disconnected integrations become explicit Unknown with owner/unblock instructions.
5. **Platform remediation adapters** — universal cards with Squarespace guided instructions, GitHub pull requests, guarded WordPress/Webflow staging/API paths, and copy/paste fallback. No adapter may publish without approval, stale-state validation, rollback, and re-audit.

Every follow-on plan must expand `AVAILABLE_CHECK_SETS`, add registry-level tests, update stored scope/check versions, and pass the same internal allowlist gate. Configuration alone must not enable an empty or partially implemented set. Historical readiness scores remain readable as legacy data.

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
