# Audit, Recommendation, and Implementation Engine — Design Spec

**Date:** 2026-06-23
**Status:** Approved

---

## 1. What This Builds

Three sequential pipeline stages that run after the tracker:

1. **Audit agent** — crawls a client's website, scores every page against 6 GEO pillars, stores results in Supabase
2. **Recommendation engine** — reads audit scores, uses Claude Haiku to generate before/after action cards for pages scoring below 60/100
3. **Implementation handlers** — when Jared approves an action card in the dashboard, a Python function delivers the change to the client's site (GitHub PR or WordPress REST API)

---

## 2. The 6 Pillars

### Scoring method per pillar

| Pillar | Method | What it checks |
|---|---|---|
| 1 — Content Structure | Haiku | Does the first paragraph directly answer a user question? Are H2/H3 headings phrased as questions? Are there bullet lists? |
| 2 — Fact Density | Haiku | How many specific numbers, percentages, and attributed claims per 200 words? Target: ≥1 per 200 words |
| 3 — Source Citations | Rules | Count external links in body content only (no nav/footer). Bonus for .gov/.edu/.org. Target: 3–5 per page |
| 4 — Authority Signals | Haiku | Press mentions, expert quotes with attribution, aggregate ratings on the page. Off-page authority (Reddit, press) is the Reddit scout's job |
| 5 — Schema Markup | Rules | Find all `<script type="application/ld+json">` blocks. Check @type (FAQPage/HowTo = high value). Flag broken JSON |
| 6 — Freshness | Rules | Find article:modified_time meta tag → `<time>` element → HTTP Last-Modified header → visible date text. Score by age in days |

Rules = deterministic Python, no LLM. Haiku = LLM call per page for that pillar. Total Haiku cost: ~$0.01–0.02/page.

### Scoring thresholds

- **0–39**: Critical
- **40–59**: Needs work — action cards generated
- **60–79**: Acceptable — no action cards, noted in summary
- **80–100**: Good

Action cards are only generated for pages scoring below 60 on any individual pillar.

---

## 3. Page Discovery

1. Fetch `https://domain.com/sitemap.xml` — parse all `<loc>` tags
2. If no sitemap: crawl homepage, follow internal `<a href>` links to depth 1
3. Cap at 20 pages per run

---

## 4. Action Cards

Each action card contains:

```
page_url        — which page
pillar          — which of the 6 pillars
score           — current score (0–100)
issue           — one sentence describing what's wrong
before          — exact current content (paragraph text, or "none" for schema)
after           — exact replacement content Haiku wrote
code_block      — for schema/meta changes: ready-to-paste code
status          — pending | approved | rejected | implemented
cms_action      — none | github_pr | wordpress_api | copy_paste
```

Pillar 4 (Authority Signals) cards never have a `cms_action` — they are always suggestion-only.

---

## 5. Implementation Handlers

### CMS type detection

During client onboarding, `cms_type` is stored on the client record. Auto-detection from HTTP response headers is a secondary fallback:
- `X-Powered-By: PHP` + `/wp-json/` accessible → `wordpress`
- `X-Generator: Webflow` → `webflow`
- GitHub repo URL present in config → `github`
- Otherwise → `copy_paste`

### Per-pillar implementation by CMS

| Pillar | GitHub | WordPress | Webflow | Squarespace/Wix |
|---|---|---|---|---|
| 1 — Content Structure | PR: replace paragraph in file | REST API: update post content | Manual if static page | Copy-paste |
| 2 — Fact Density | PR: insert sentences into file | REST API: update post content | Manual if static page | Copy-paste |
| 3 — Source Citations | PR: wrap text in anchor tag | REST API: update post content | Manual if static page | Copy-paste |
| 4 — Authority Signals | Suggestion only | Suggestion only | Suggestion only | Suggestion only |
| 5 — Schema Markup | PR: inject JSON-LD into `<head>` | REST API: update head via plugin | Webflow API: custom code | Copy-paste into code injection |
| 6 — Freshness | PR: update meta tag date | REST API: update modified date | Manual | Copy-paste |

### GitHub implementation

Requires: client config includes `github_repo` (owner/repo) and system has a GitHub token with contributor access.

Flow:
1. Fetch current file content via GitHub API
2. Apply string replacement (before → after)
3. Create a new branch `vv-audit-{pillar}-{date}`
4. Open PR with description of what changed and why

### WordPress implementation

Requires: `wordpress_url` and `wordpress_app_password` in client config (application password, no plugin needed).

Flow:
1. GET `/wp-json/wp/v2/pages?slug={slug}` to find the post ID
2. PATCH `/wp-json/wp/v2/pages/{id}` with updated content
3. For schema: inject into `yoast_head_json` if Yoast is installed, otherwise prepend to content

### Copy-paste fallback

For any CMS that can't be automated, or for content changes on non-automatable platforms, the dashboard shows:
- The exact text or code block to copy
- Step-by-step instructions for where to paste it in their CMS

---

## 6. Database Schema Additions

Three new tables added to the existing schema:

```sql
audit_runs       — one row per audit run (client_id, ran_at, pages_audited, site_score, pillar_averages, weakest_pillar)
page_scores      — one row per page per run (run_id, url, title, word_count, total_score, pillar_scores jsonb)
action_cards     — one row per recommendation (run_id, page_url, pillar, score, issue, before_text, after_text, code_block, status, cms_action)
```

`clients` table gets two new columns:
```sql
cms_type         — text: 'github' | 'wordpress' | 'webflow' | 'copy_paste'
cms_config       — jsonb: github_repo, wordpress_url, wordpress_app_password, etc.
```

---

## 7. Dashboard Additions

Two new admin pages:

**`/admin/audit/[clientId]`** — audit history list, site score trend, weakest pillar callout, link to latest run

**`/admin/audit/[clientId]/[runId]`** — page-by-page pillar score table, action cards for this run grouped by pillar, approve/reject buttons per card, copy-paste instructions for non-automated cards

Existing `/admin/approvals` page may be extended or the audit run page handles approvals inline — TBD based on UX preference.

---

## 8. CLI Entry Points

Follows exact same pattern as `run.py`:

```
python audit.py ../clients/childspot.json          # crawl + score, output JSON
python audit.py --client-id <uuid> --upload        # upload results to Supabase

python recommend.py --run-id <uuid>                # generate action cards for a run
python recommend.py --client-id <uuid> --latest    # run against most recent audit
```

---

## 9. Demo Setup

The implementation handlers are tested against:
- **GitHub**: Jared's own website repo (full contributor access as author)
- **WordPress**: deferred until a client provides credentials
- **Copy-paste**: always works, no setup needed

All audit and recommendation features work against any public URL with no special access.

---

## 10. What This Does Not Cover

- Reddit scout (deferred — commercial API required)
- LangGraph orchestration (Phase 7 per original build order)
- Client-facing audit dashboard (admin-only for now)
- Webflow API integration (copy-paste fallback used until a Webflow client onboards)
- Auto-scheduling audit runs (deferred — manual trigger via CLI or dashboard button)
