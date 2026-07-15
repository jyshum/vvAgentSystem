# Technical Audit V1 Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the entire remaining Technical Audit V1 — Protocol, Site Integrity, and Performance check sets; finding grouping and lifecycle; the unified result/action workflow with stale-state protection, approval, Squarespace guided remediation, and deterministic re-audit verification; backend APIs; and finally the deferred frontend cutover — validated end to end without creating a production baseline.

**Architecture:** Extend the existing bounded collector (`agents/src/technical_audit/collector.py`) into a full evidence layer (robots, sitemaps, TLS, HTTP probe, external links, images, structured data, performance APIs), register every new check in the versioned five-state registry, compute deterministic finding keys/lifecycle/grouping at persistence time, and add a purpose-built workflow table (migration 018) plus authenticated FastAPI endpoints. Immutable observations/results stay separate from editable workflow cards. AI never participates in the technical path; ambiguity is `review`. The frontend cutover happens last, only after all backend infrastructure is verified.

**Tech Stack:** Python 3.14 venv (`agents/.venv`), FastAPI, httpx, BeautifulSoup, `protego` (robots parsing, new dep), stdlib `ssl`/`json`/`xml.etree`, Supabase PostgreSQL, pytest, Next.js/React/Vitest (frontend phase only).

**Normative documents (unchanged, binding):**
- `docs/superpowers/specs/2026-07-14-deterministic-technical-audit-design.md`
- `docs/superpowers/specs/2026-07-14-v1-simplification-technical-audit-expansion-design.md`
- `docs/superpowers/specs/2026-07-15-technical-audit-reset-engine-first-design.md`

## Global Constraints

- Five deterministic statuses only: `pass`, `fail`, `review`, `unknown`, `not_applicable`.
- No matcher/similarity logic, proprietary scores, heuristic technical decisions, legacy fallbacks, automatic publishing, or scheduling.
- No LLM call anywhere in the technical audit path. Semantic judgment becomes `review` with a named question.
- Every collector is bounded (pages, bytes, redirects, timeouts, counts, concurrency) and records provenance; limits reached are disclosed in scope, never silently passed.
- SSRF protections on every fetch: public-DNS validation, HTTPS/same-site for internal crawl, credential-URL rejection, redirect validation, byte caps.
- Squarespace `llms.txt` absence stays Not Applicable; missing descriptions on audited canonical indexable pages stay Review.
- Unknown never means "probably fine"; an unavailable integration never makes an independent public check Unknown.
- No production baseline: the persisted CLI is never pointed at production Supabase. BudgetYourMD validation is the non-persisting smoke command only.
- Rules change by adding a check version, never by silently reinterpreting version 1.
- TDD per task; commit per task.

## Product decisions resolved from the approved documents

1. **Mixed content evidence source.** No headless browser exists in this runtime. Mixed content is evaluated deterministically from raw HTML: `http://` URLs in active-content attributes (`script src`, `link href` for stylesheets, `iframe src`, `img src`, `source src/srcset`, `video/audio src`, `object data`, `form action`) on HTTPS pages fail; ordinary `<a href="http://…">` hyperlinks are excluded per spec. Scope records `evidence: raw_html` so a later rendered-DOM version can be check version 2.
2. **Structured data parsing.** JSON-LD (including arrays and `@graph`) is parsed deterministically with `json`. RDFa/Microdata are *detected* (`typeof`/`itemscope` attributes); when present they produce `review` ("non-JSON-LD structured data present; verify with a structured-data validator") rather than a half-parsed verdict. This follows the AI-boundary rule that unsupported evidence becomes review, not a fabricated decision.
3. **Existing-source support without AI.** V1 audits existing citation links deterministically: link health, retrievability, content type, and stored evidence excerpts. Claim-to-passage semantic comparison is AI-class work and is out of the deterministic path; pages whose editorial content contains external citation links get link-health results, and the check records that semantic support verification requires review. Pages with no external content links are `not_applicable`.
4. **Soft 404.** A 200 response whose `<title>` contains "404" or "not found" (case-insensitive) is `review` ("possible soft 404"), never `fail` — deterministic string evidence, bounded judgment.
5. **Bing.** No Bing integration exists. When `BING_WEBMASTER_API_KEY` is unset the check is `unknown` with owner `integration` and the unblock action "Connect Bing Webmaster Tools" (the spec's "disconnected but expected" example). When set, submission status is retrieved and evaluated; API failure is `unknown`.
6. **CrUX / Lighthouse (PSI).** `CRUX_API_KEY` unset → `unknown` (unblock: configure key). Lighthouse lab uses three PageSpeed Insights mobile runs; the median Performance score maps 90–100 pass / 50–89 review / <50 fail, displayed as an external diagnostic. PSI key unset → `unknown`. The LCP lazy-load rule reads PSI's `lcp-lazy-loaded` audit; when LCP is text it is `not_applicable`.
7. **GSC sitemap check scope.** In scope when `clients.gsc_site_url` is nonempty; empty → `not_applicable` (explicitly unconfigured). Credential/API failure → `unknown`.
8. **Staging validation** = local Supabase (development database), per the operator guide's Task-12 definition. There is no separate staging deployment.
9. **Alt text.** Content `<img>` without an `alt` attribute fails; `alt=""` passes as declared-decorative; alt equal to the image filename/URL or containing obvious stuffing (≥ 4 comma-separated repeats) is `review`. Informative-vs-decorative intent is bounded judgment → `review` only when evidence conflicts (empty alt inside a link with no other text fails per link-purpose rule).
10. **Freshness classification.** Deterministic: pages with Article/BlogPosting JSON-LD or a visible byline+date pattern are dated editorial; others are timeless/utility (`not_applicable` for staleness). Date validity (parseable, nonfuture, `dateModified >= datePublished`, schema/visible consistency) is checked wherever dates exist. No stored history → change verification `unknown` (baseline established).

## Check inventory (all version 1)

| Set | check_id | scope | Evidence |
|---|---|---|---|
| protocol | `robots_txt.integrity` | site | robots fetch: real text response, not HTML fallback, parseable |
| protocol | `robots_txt.access` | site | protego effective access for versioned crawler registry against homepage + sampled pages + sitemap |
| protocol | `sitemap.discovery` | site | conventional + robots-declared locations |
| protocol | `sitemap.integrity` | site | XML/UTF-8/absolute URLs/host/scheme/50k-limit, index + bounded children, lastmod validity |
| protocol | `sitemap.coverage` | site | key-page (homepage/nav canonical) presence |
| protocol | `sitemap.entry_health` | site (sampled) | direct 200/indexability/canonical consistency of sampled entries |
| protocol | `tls.certificate` | site | chain/hostname validity, expiry windows 30/8/7 days |
| protocol | `tls.https_redirect` | site | HTTP→HTTPS behavior, loops, wrong destinations, canonical variants |
| protocol | `tls.mixed_content` | page | raw-HTML active mixed content |
| protocol | `schema.integrity` | page | JSON-LD parse, arrays/@graph, malformed/placeholder/duplicate/conflict/unhealthy URL |
| protocol | `schema.coverage` | page | homepage Organization/WebSite review; FAQ never required |
| site_integrity | `links.internal_health` | page | collected internal targets + bounded probes; 404/410/5xx/loops/fragments |
| site_integrity | `links.external_health` | site (sampled) | deduped bounded external probes with unknown for 403/429 |
| site_integrity | `images.integrity` | page | load/MIME/HTTPS/bytes for sampled images |
| site_integrity | `images.alt_text` | page | alt attribute presence/validity |
| site_integrity | `freshness.dates` | page | date validity/ordering/consistency; staleness signals |
| site_integrity | `source_support.link_health` | page | citation-link health + evidence excerpts |
| performance | `performance.crux` | page+origin | CrUX p75 LCP/INP/CLS thresholds |
| performance | `performance.lighthouse` | page (sampled) | median of three PSI mobile runs, lab diagnostic |
| performance | `performance.lcp_image` | page (sampled) | PSI `lcp-lazy-loaded`; NA when LCP is text |
| performance | `integration.gsc_sitemap` | site | GSC sitemap submission/processing |
| performance | `integration.bing` | site | Bing submission; unknown when disconnected |

Severity assignments follow the design spec (expired cert = critical fail; cross-domain canonical = critical; most integrity defects = high; review-class = medium/low).

## File structure

New backend files:

- `agents/src/technical_audit/evidence/robots.py` — robots fetch + protego wrapper + crawler registry.
- `agents/src/technical_audit/evidence/sitemaps.py` — discovery, bounded parse, entry model.
- `agents/src/technical_audit/evidence/tls.py` — certificate + HTTP-probe evidence.
- `agents/src/technical_audit/evidence/links.py` — link/image inventory extraction + bounded probing.
- `agents/src/technical_audit/evidence/structured_data.py` — JSON-LD extraction + RDFa/Microdata detection.
- `agents/src/technical_audit/evidence/performance.py` — CrUX + PSI collectors (mockable HTTP).
- `agents/src/technical_audit/checks/robots.py`, `checks/sitemap.py`, `checks/tls.py`, `checks/schema_markup.py`, `checks/links.py`, `checks/images.py`, `checks/freshness.py`, `checks/source_support.py`, `checks/performance.py`, `checks/integrations.py`
- `agents/src/technical_audit/lifecycle.py` — finding keys, run-over-run lifecycle, deterministic grouping.
- `agents/src/technical_audit/workflow.py` — card creation, state machine, stale-state guard, verification.
- `agents/src/technical_audit/remediation.py` — remediation catalogue incl. Squarespace guided steps.
- `supabase/migrations/018_technical_audit_workflow.sql`
- `agents/tests/technical_audit/fixtures/…` — HTML/XML/robots/PSI/CrUX fixtures.
- `agents/tests/technical_audit/test_robots.py`, `test_sitemaps.py`, `test_tls.py`, `test_schema_markup.py`, `test_links.py`, `test_images.py`, `test_freshness.py`, `test_source_support.py`, `test_performance.py`, `test_integrations.py`, `test_lifecycle.py`, `test_workflow.py`, `test_remediation.py`, `test_repeatability.py`
- `agents/tests/test_workflow_api.py`

Modified: `collector.py` (new evidence fields), `checks/__init__.py` (set registration), `runner.py` (site observations for new evidence), `pipeline.py` (lifecycle/groups/cards persistence), `observations.py` (links/images/schema/date extraction), `server.py` (workflow APIs), `cli.py` (`--check-sets` argument), `agents/pyproject.toml` + `requirements.txt` (protego), `supabase/schema.sql`, `PROJECT_STATE.md`, `docs/technical-audit-operations.md`.

Frontend phase (last): `dashboard/` cutover off deleted legacy schema; unified card components; run view + action inbox.

---

## Phase 0 — Foundation validation gate (tranche-0 Task 12)

### Task 0.1: Local Supabase validation, demo persistence, smoke, production-zero

- [ ] Start/reset local Supabase (`supabase start`, `supabase db reset`) — migrations 001–017 apply cleanly.
- [ ] Seed demo client `11111111-1111-1111-1111-111111111111` and query `22222222-…` exactly as tranche-0 Task 12 Step 2.
- [ ] Run targeted backend suite: `cd agents && .venv/bin/python -m pytest -q` (251 expected).
- [ ] Persisted demo audit against local DB only: `SUPABASE_URL=<local> SUPABASE_SERVICE_KEY=<local> .venv/bin/python -m src.technical_audit.cli run --client-id 11111111-1111-1111-1111-111111111111` → completed run, bounded observations, Foundation results.
- [ ] Non-persisting BudgetYourMD smoke: `cli smoke --domain budgetyourmd.ca --platform squarespace --output ../.artifacts/technical-audit/budgetyourmd-foundation-smoke.json` → bare→www redirect accepted, Squarespace llms.txt NA, every result carries evidence/applicability/scope/next action.
- [ ] Verify production counts remain `1, 8, 0, 0, 0, 0` (clients, queries, tracker_runs, pipeline_runs, improvement_runs, technical_audit_runs).
- [ ] Record evidence in `PROJECT_STATE.md`; commit docs.

## Phase 1 — Evidence layer expansion

### Task 1.1: Extend `CollectedSite` with protocol/site evidence

**Files:** modify `collector.py`; tests `test_collector.py`.

`CollectedSite` gains defaulted fields so existing construction keeps working:

```python
@dataclass(frozen=True)
class CollectedSite:
    identity: SiteIdentity
    homepage: HttpEvidence
    pages: tuple[HttpEvidence, ...]
    llms_txt: HttpEvidence
    scope: dict[str, Any]
    robots_txt: HttpEvidence | None = None
    sitemaps: tuple[HttpEvidence, ...] = ()
    tls: dict[str, Any] | None = None
    http_probe: HttpEvidence | None = None
    external_probes: tuple[HttpEvidence, ...] = ()
    image_probes: tuple[HttpEvidence, ...] = ()
```

`collect_site(identity, …)` (superset of `collect_foundation`, which becomes a thin alias) additionally:
- fetches `/robots.txt` (same bounded fetcher);
- retains sitemap documents it already fetches (conventional `/sitemap.xml` is queued even when not linked) instead of discarding them;
- gathers TLS evidence via `ssl` handshake to the final homepage host (cert subject/SANs/notBefore/notAfter/issuer, verified with default context; handshake failure recorded as error evidence, never an exception);
- probes `http://<domain>/` with a redirect-recording (not following past 5 hops) plain-HTTP fetcher to observe HTTP→HTTPS behavior — this probe is exempt from the HTTPS-only rule but never sends credentials and caps bodies at 4 KB;
- probes deduplicated external link targets (cap 50 site-wide) and sampled image URLs (cap 40 site-wide) with `validate_public_resolution`, HEAD-then-GET fallback, 64 KB body cap, and per-request timeout; external redirect chains are recorded but hosts are not restricted to the site (they are external by definition) while still rejecting private/credentialed targets;
- scope gains `external_probe_limit`, `image_probe_limit`, counts, and per-category truncation flags.

Bounds: `MAX_EXTERNAL_PROBES = 50`, `MAX_IMAGE_PROBES = 40`, `MAX_SITEMAP_ENTRIES = 200` parsed per document, existing `MAX_SITEMAPS = 3`.

TDD: fake-fetcher tests for robots retained, sitemap docs retained, TLS evidence recorded via injected `tls_inspector`, http probe recorded, external/image caps enforced and disclosed, private-address external target rejected.

### Task 1.2: Page observation enrichment

**Files:** modify `observations.py`; tests `test_observations.py`.

`extract_page_observation` additionally extracts (bounded):
- `links`: internal/external hrefs with anchor text, rel, and fragment (cap 200/page, each ≤ 2048 chars), classified `internal`/`external` against the site identity (identity passed in);
- `images`: src (resolved), alt (None when attribute absent, "" when empty), loading attr, width/height attrs, inside-link flag (cap 60/page);
- `active_mixed_candidates`: http:// URLs in active-content attributes (cap 50);
- `jsonld_blocks`: raw `<script type="application/ld+json">` texts (cap 20 blocks, 8 KB each), plus `has_rdfa`/`has_microdata` booleans;
- `visible_dates`: ISO/verbose date strings from `<time datetime>` and common byline patterns (cap 10);
- `h1_texts` already exists.

## Phase 2 — Protocol check set

### Task 2.1: robots.txt evidence + checks

Add `protego` to `pyproject.toml`/`requirements.txt` and install. `evidence/robots.py` defines the versioned crawler registry:

```python
CRAWLER_REGISTRY_VERSION = 1
RELEVANT_CRAWLERS = (
    "Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "PerplexityBot", "ClaudeBot", "Claude-User", "Google-Extended", "CCBot",
)
```

`checks/robots.py`:
- `robots_txt.integrity`: 200 + text/plain-ish + parseable → pass; HTML fallback (content-type text/html or body starts with `<`) → fail; 404/absent → pass-with-advisory (`review` only if sitemap relies on robots declaration — otherwise pass, summary "missing robots.txt semantically allows crawling (advisory)"); 403/429/5xx/transport error → unknown.
- `robots_txt.access`: for each registry crawler, protego `can_fetch` on homepage, sampled collected public pages, and the discovered sitemap URL; all allowed → pass; a configured crawler blocked from homepage or a sampled public page → fail with the exact matching rule; blocked only on non-priority paths → review (intentional privacy preserved); robots unavailable (unknown above) → unknown. Do not require explicit `Allow: /`. Synthetic requests are supporting evidence only — scope notes `delivery_confirmed: false`.

Five-status fixture tests per check, including precedence/wildcard/end-anchor fixtures parsed by protego.

### Task 2.2: sitemap evidence + checks

`evidence/sitemaps.py`: discovery list (robots `Sitemap:` declarations + `/sitemap.xml` convention + homepage `<link rel=sitemap>`), bounded parse producing `SitemapDocument(url, kind: index|urlset|invalid, entries: tuple[SitemapEntry,...], parse_error)` with `SitemapEntry(loc, lastmod)`; entries capped at 200/document with truncation disclosure.

`checks/sitemap.py`:
- `sitemap.discovery`: found at conventional or declared location → pass; none found → review ("site may rely on navigation-only discovery"); fetch blocked → unknown.
- `sitemap.integrity`: valid XML/UTF-8, absolute same-site URLs, http(s) scheme, well-formed index/children, ≤ 50 000 entries; malformed XML or HTML fallback → fail; relative/foreign-host URLs → fail; invalid/future `lastmod` when present → fail (validity) — credibility questions → review.
- `sitemap.coverage`: homepage + primary-navigation canonical pages present → pass; a key page missing while the site serves a sitemap → fail; other discovered pages missing → review; no sitemap → not_applicable (covered by discovery).
- `sitemap.entry_health`: sample min(entries, 10) deterministically (first N in document order, disclosed as sampled); direct 200 canonical indexable → pass; redirect/404 entries → fail; 403/429/transport → unknown.

### Task 2.3: TLS/HTTPS checks

`evidence/tls.py`: `inspect_tls(host, port=443, timeout=10) -> dict` using `ssl.create_default_context()`; returns subject/issuer/SANs/not_before/not_after/`verified: True` or `{"error": <class>, "verified": False}`. Injected into `collect_site` for testability.

`checks/tls.py`:
- `tls.certificate`: verified handshake + hostname match (via successful default-context connect to final host) and days-to-expiry > 30 → pass; 8–30 → review; ≤ 7 → fail (high); expired/invalid chain/hostname mismatch → fail (critical); handshake could not be attempted (network) → unknown.
- `tls.https_redirect`: http probe redirects (301/302/307/308) to allowed HTTPS host → pass; redirect loop, downgrade, or wrong-host destination → fail; port 80 unreachable → review ("verify plain-HTTP requests reach the HTTPS site"); probe error → unknown.
- `tls.mixed_content` (per page): no active mixed candidates → pass; any active candidate → fail listing exact URLs; page unavailable → unknown; non-HTML → not_applicable. Plain hyperlinks never count.

### Task 2.4: schema markup checks

`evidence/structured_data.py`: `parse_jsonld(blocks) -> list[dict]` handling arrays and `@graph` flattening, recording per-block parse errors; placeholder detector (`example.com`, `lorem`, `changeme`, empty required `name`/`url` strings); duplicate-entity detector (same `@type` + same `@id` or same normalized `name` twice on one page).

`checks/schema_markup.py`:
- `schema.integrity`: no structured data → not_applicable; all JSON-LD blocks parse with no placeholder/duplicate/conflict and any same-site URLs inside are allowed-host HTTPS → pass; malformed JSON block or placeholder value → fail; duplicate/conflicting entities or schema URL pointing to a collected 404 page → fail; contradiction requiring judgment (e.g., `dateModified < datePublished` handled in freshness; org name differing from visible H1/brand) → review; RDFa/Microdata present → review per product decision 2.
- `schema.coverage`: homepage without Organization/WebSite → review; non-homepage pages → not_applicable in v1 (no verified-profile editorial classification exists); FAQPage present → integrity validates it, but FAQ schema is never required.

### Task 2.5: registry + runner wiring for `protocol`

`build_v1_registry` accepts any subset of `("foundation", "protocol", "site_integrity", "performance")`, registering per set; unknown names still raise. `runner.py` builds site observations for robots/sitemaps/tls/http_probe/external/image probes (kind-tagged, bounded excerpts — robots body ≤ 16 KB excerpt, sitemap bodies excerpted to first 4 KB with entry counts in data) and passes identity into page extraction. `AuditContext.site_observations` keys: `llms_txt`, `robots_txt`, `sitemaps` (tuple), `tls`, `http_probe`, `external_probes`, `image_probes`.

`pipeline.py` `FOUNDATION_CHECK_SETS` becomes `DEFAULT_CHECK_SETS = ("foundation", "protocol", "site_integrity", "performance")` only at the END of Phase 6 validation; until then the pipeline default stays `("foundation",)` and the CLI gains `--check-sets` for explicit expansion during development.

## Phase 3 — Site Integrity check set

### Task 3.1: link checks

`checks/links.py`:
- `links.internal_health` (per page): every internal link target that was collected or probed resolves 200/expected-redirect → pass; confirmed 404/410/repeated 5xx/loop → fail; unnecessary internal redirect (301 to another collected 200 page) → review; fragment links whose target page was collected but lacks the anchor id → fail; soft-404 title signal → review; 403/429/transport → unknown; `mailto:`/`tel:`/`sms:`/logout/admin → excluded (not results). Shared-cause grouping happens in Phase 5 via identical broken destination.
- `links.external_health` (site, sampled): deduped external probes; 200 → pass; 404/410/DNS/TLS failure → fail; 403/429/timeout/paywall-status → unknown; probe cap reached → scope discloses sampling; zero external links → not_applicable.

### Task 3.2: image checks

`checks/images.py`:
- `images.integrity` (per page): sampled probed images load with image/* MIME over HTTPS → pass; broken load/HTML-fallback/HTTP source → fail; probe blocked → unknown; page without images → not_applicable. No byte caps or WebP mandates; measured bytes recorded as evidence only.
- `images.alt_text` (per page): all content images carry an alt attribute (empty allowed as declared-decorative) → pass; any missing attribute → fail; filename-as-alt/stuffing, or empty-alt image as the only content of a link → review/fail per decision 9; no images → not_applicable.

### Task 3.3: freshness checks

`checks/freshness.py` — `freshness.dates` per page: classify via decision 10. For dated pages: all dates parseable, nonfuture, `dateModified >= datePublished`, schema/visible dates consistent (same day when both present) → pass; violation → fail; staleness signals (explicit past year presented as current in title, expired event dates in schema) → review; no history available for change verification → the result records `change_verification: "unknown_baseline"` in observed while date-validity still determines status; timeless/utility pages → not_applicable. Never a 90-day rule.

### Task 3.4: source support

`checks/source_support.py` — `source_support.link_health` per page: external links inside main content (exclude nav/footer by tag ancestry recorded at extraction) are citation candidates. Healthy retrievable target → pass with stored evidence excerpt reference; dead/contradictory-status → fail; blocked → unknown; no content external links → not_applicable. Observed data stores publisher host, retrieval time, fingerprint, and a bounded excerpt; semantic claim comparison is explicitly recorded as out-of-scope-for-v1 in the result's `scope`.

## Phase 4 — Performance check set

### Task 4.1: CrUX + PSI collectors

`evidence/performance.py`, all HTTP via injected `http_post`/`http_get` callables (httpx defaults), never raising:
- `fetch_crux(url, api_key, form_factor="PHONE")` → page-level record, origin fallback flagged `origin_fallback: True`; 404 from API = insufficient data.
- `fetch_psi(url, api_key, runs=3)` → three sequential mobile runs; returns per-run scores/metrics + medians + provenance (lighthouse version, fetch time, throttling from response). Missing key → `{"unavailable": "missing_api_key"}`.

### Task 4.2: performance checks

`checks/performance.py`:
- `performance.crux`: p75 thresholds LCP ≤ 2.5 s / INP ≤ 200 ms / CLS ≤ 0.1 pass; review/fail bands per spec table; worst metric determines status, each metric reported in observed; insufficient data or missing key → unknown; origin-level data labelled in summary.
- `performance.lighthouse`: median of three mobile scores; 90+ pass, 50–89 review, <50 fail; observed stores all three run scores + provenance; labelled "external lab diagnostic"; lab never passes INP (INP excluded from lab observed; TBT recorded as diagnostic only); missing key/API failure → unknown. Sampled subjects: homepage + up to 2 more collected nav pages (deterministic first-N, disclosed).
- `performance.lcp_image`: from PSI `lcp-lazy-loaded` + `largest-contentful-paint-element` audits; LCP image lazy-loaded → fail; LCP text → not_applicable; PSI unavailable → unknown.

### Task 4.3: integration checks

`checks/integrations.py`:
- `integration.gsc_sitemap`: `gsc_site_url` empty → not_applicable; else call Search Console `sitemaps().list` via existing `src/gsc.py` credentials: submitted + processed without errors and covering the discovered sitemap → pass; submitted-but-errors → fail; discovered sitemap never submitted → review; credential/API failure → unknown. Public sitemap checks stay independent.
- `integration.bing`: per decision 5.

Context change: `AuditContext` gains `integrations: dict[str, Any]` (gsc_site_url, api-key presence booleans, injected fetch results) populated by the pipeline/CLI, so evaluators stay pure.

## Phase 5 — Finding lifecycle and grouping

### Task 5.1: deterministic finding keys + lifecycle

`lifecycle.py`:

```python
def finding_key(client_id, check_id, check_version, subject, material) -> str  # sha256
def material_evidence(result: dict) -> dict  # status-relevant observed subset per check family
def classify_lifecycle(current: list[dict], previous: list[dict]) -> list[dict]
```

Rules: same key both runs, same status → `continuing`; same key, material change → `changed`; key absent previously → `new`; previous non-pass key now passing → current pass result marked `resolved`; previous pass now non-pass → `regressed`. Pure functions over result dicts; persistence passes the previous completed run's results.

### Task 5.2: deterministic grouping

`group_findings(results) -> list[dict]`: group key = sha256 of `(check_id, remediation_id, canonical shared-cause signature)` where the signature is, per family: broken destination URL for links, identical missing-alt filename set n/a (images group by identical `summary` + `remediation_id`), template title/description duplicate value for metadata, shared sitemap document for sitemap entries. Only same-cause groups; no similarity logic. Output rows: `group_key, check_id, remediation_id, summary, subjects (sorted), result_indices`.

### Task 5.3: persistence

`pipeline.py`: after inserting results, fetch previous completed run's results for lifecycle classification, update `lifecycle_state` on the inserted rows, insert groups into `technical_audit_finding_groups` (migration 018), and store `check_sets`+`registry_versions` in run scope.

## Phase 6 — Unified workflow, APIs, migration 018

### Task 6.1: migration 018

```sql
create table public.technical_audit_finding_groups (
  id uuid primary key default gen_random_uuid(),
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  group_key text not null,
  check_id text not null,
  remediation_id text,
  summary text not null,
  subjects text[] not null default '{}',
  created_at timestamptz not null default now(),
  unique (audit_run_id, group_key)
);

create table public.technical_audit_action_cards (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  audit_run_id uuid not null references public.technical_audit_runs(id) on delete cascade,
  group_key text,
  source text not null default 'technical' check (source in ('technical', 'community')),
  status text not null default 'observed' check (status in (
    'observed', 'draft_prepared', 'approved', 'rejected',
    'applied', 'verified', 'still_failing', 'stale')),
  title text not null,
  platform text not null,
  implementation_mode text not null,
  instructions jsonb not null default '[]'::jsonb,
  copy_values jsonb not null default '{}'::jsonb,
  precondition jsonb not null default '{}'::jsonb,
  approved_by text,
  approved_at timestamptz,
  applied_at timestamptz,
  verification jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.technical_audit_card_results (
  card_id uuid not null references public.technical_audit_action_cards(id) on delete cascade,
  result_id uuid not null references public.technical_audit_results(id) on delete cascade,
  primary key (card_id, result_id)
);
```

Plus indexes, RLS mirroring the 014 policy pattern, and a `finding_key text` column on `technical_audit_results`. Contract test asserts tables/columns/policies exist in migration text and that nothing legacy is recreated.

### Task 6.2: remediation catalogue

`remediation.py`: `CATALOGUE: dict[str, RemediationEntry]` where each entry defines `risk`, `modes_by_platform` (squarespace → guided, others → guided in v1; no adapter writes), and `build_guidance(result) -> {title, instructions[], copy_values{}}` producing platform-specific deterministic steps (Squarespace: SEO title/description fields, page settings for sitemap/canonical, SSL panel routes — matching spec's Squarespace safety rules; never editing generated XML or fabricating file editors). Unknown remediation_id → mode `unavailable` with explanation; the finding stays visible.

### Task 6.3: workflow state machine + stale-state guard + verification

`workflow.py`:

```python
ALLOWED_TRANSITIONS = {
    "observed": {"draft_prepared"},
    "draft_prepared": {"approved", "rejected"},
    "approved": {"applied", "rejected", "stale"},
    "applied": {"verified", "still_failing"},
    "stale": {"draft_prepared"},
}
def create_cards(sb, run, results, groups, client) -> list[dict]      # fail/review + human/integration-owned unknown
def approve_card(sb, card_id, approver) -> dict
def mark_applied(sb, card_id, *, fetcher=None) -> dict                # stale-state guard first
def verify_card(sb, card_id, *, fetcher=None) -> dict                 # deterministic re-audit of the exact checks
```

`mark_applied` re-fetches each precondition subject, compares the stored evidence fingerprint; changed → status `stale`, refusal recorded, no state advance to applied. (The operator applies changes manually on Squarespace; `mark_applied` is the explicit human assertion gated by freshness of the draft's basis — wait, the guard refuses when the page is UNCHANGED since audit? No: precondition holds the *audited defective* fingerprint; `mark_applied` records the operator's claim; `verify_card` is the deterministic authority.) Precisely: `mark_applied` requires card approved and records applied_at; `verify_card` re-collects the subjects, re-runs the originating check ids via the registry, and sets `verified` only when every linked check passes, else `still_failing`, storing fresh evidence in `verification`. The stale guard applies to `approve→applied` for draft-bearing cards: if the subject fingerprint no longer matches the audited precondition, the draft's copy values may be outdated → `stale`.

System-owned retry Unknowns create no card. Nothing auto-approves; no endpoint publishes to any website.

### Task 6.4: backend APIs

`server.py` (all under existing bearer auth):
- `GET /api/technical-audit/runs?client_id=` and `GET /api/technical-audit/runs/{run_id}` (run + summary + results + groups)
- `GET /api/technical-audit/cards?client_id=&status=`
- `POST /api/technical-audit/cards/{card_id}/approve` (body: approver)
- `POST /api/technical-audit/cards/{card_id}/reject`
- `POST /api/technical-audit/cards/{card_id}/mark-applied`
- `POST /api/technical-audit/cards/{card_id}/verify`

404 for schedule/approval-resume endpoints unchanged. TestClient tests: auth required, transition rules enforced (409 on illegal transition), stale guard produces `stale`, verify only flips on deterministic pass.

### Task 6.5: pipeline + CLI integration

`pipeline.py` creates cards after results/groups; CLI `run` accepts `--check-sets` (default all four once Phase 6 tests pass); `smoke` accepts `--check-sets` too, defaulting to all four, still never touching Supabase; performance checks in smoke run against real APIs only when keys exist, else produce `unknown` — deterministic and safe.

## Phase 7 — Complete validation (no production baseline)

### Task 7.1: fixtures + repeatability + adversarial suites

- Fixture-driven five-status coverage for every new check (each `test_*.py` includes at least one pass/fail/review/unknown/not_applicable case where the status is reachable).
- `test_repeatability.py`: same fake-fetcher evidence run twice → byte-identical statuses and summaries.
- Adversarial: oversized bodies truncated-and-disclosed, malformed MIME, redirect to private address rejected, credential URL rejected, robots/sitemap HTML fallbacks, prompt-injection-shaped page text changes nothing (no AI in path — assert no LLM modules imported by `src.technical_audit`).

### Task 7.2: staging (local Supabase) + demo persistence with all check sets

- Apply migration 018 locally (`supabase db reset`), re-seed demo client.
- `cli run --client-id 111… --check-sets foundation,protocol,site_integrity,performance` against local DB → completed run, results in all sections, groups + cards created, lifecycle states populated; second run → `continuing`/`resolved` lifecycle proof.
- Full suites: `pytest -q` green; `rg` scans prove no matcher/scorer/legacy imports.

### Task 7.3: BudgetYourMD non-persisting smoke (full sets) + production checks

- `cli smoke --domain budgetyourmd.ca --platform squarespace --check-sets …` → artifact reviewed: www redirect, Squarespace NA rules, TLS pass expected, integrations unknown (no keys in smoke env), zero DB writes.
- Production counts still `1, 8, 0, 0, 0, 0`; migration 018 applied to production only as schema (empty tables) after review — **production data rows remain zero; no baseline run**.
- Update `PROJECT_STATE.md` + `docs/technical-audit-operations.md`; code review over the whole range; verification-before-completion.

## Phase 8 — Frontend cutover (after all backend work)

- Remove dashboard dependencies on deleted legacy schema (approvals views, pages-tab, matcher/score presentations, schedule copy).
- Unified card component rendering status/title/subject/checked/observed/why/scope/confidence/next action/implementation mode/instructions/approval/verification; collapse pass + not_applicable; open fail/review/unknown.
- Technical audit run view (summary by status, sections, groups) and filtered action inbox (fail/review/human-owned unknown/community).
- No total score anywhere; Lighthouse labelled external diagnostic.
- Vitest suites + production build; validation against local Supabase data from Task 7.2.

Detailed frontend task breakdown is written at the start of Phase 8, after the backend API shapes are frozen — per the approved instruction that frontend follows completed backend infrastructure.

---

## Self-review notes

- Spec coverage: all thirteen audit sections are mapped to check ids or explicit v1 product decisions (citations → decision 3; images LCP → decision 6; page speed field/lab split → Tasks 4.1–4.2; grouping/lifecycle → Phase 5; remediation safety contract → Phase 6; fixtures/tests → Phase 7; frontend → Phase 8).
- Prohibited surfaces verified absent by scans in Task 7.2.
- Statuses, thresholds, and Squarespace rules quoted from the normative spec, not re-derived.
