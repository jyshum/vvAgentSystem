# Deterministic Technical Audit and Safe Remediation — Design Spec

**Status:** Approved section by section; consolidated for final review

**Date:** 2026-07-14

**Scope:** Replace the technical/citation-readiness scoring path in the improvement pipeline. Query generation, query paraphrasing, tracking, competitive-gap measurement, and query-to-page matching remain separate concerns.

## Decision Summary

The technical observation layer will be a versioned checklist, not a proprietary score.

One audit engine gathers production-site evidence and evaluates independent checks. Each check returns one of five statuses—`pass`, `fail`, `review`, `unknown`, or `not_applicable`—plus its evidence, scope, applicability reason, and exact next step. Deterministic software decides observable facts. AI may organize evidence, compare semantic content, or draft a constrained remediation, but it cannot invent facts, sources, dates, authors, or publish a change.

This is intentionally simpler than the current scoring/card system while being technically deeper. Quality comes from evidence, applicability, safe state transitions, and verification—not from more agents or a more elaborate score.

## Why the Current Run Produces Unreliable Cards

The latest behavior is explained by hard-coded rules and prompts in the codebase, rather than by a trustworthy research or evidence layer:

- `agents/src/improvement/scorer.py` assigns points for arbitrary proxies including word count, list count, FAQ schema, author credentials, link count, and a universal 90-day freshness threshold.
- `agents/src/improvement/card_generator.py` turns those scores directly into action types. It states that pages with three citations are 2.8 times more likely to be cited, requires FAQ schema when absent, and claims citation rates drop after three months.
- The same generator asks an LLM to invent “example authoritative URLs,” generate FAQ content, create broad schema, and set a modification tag to today's date.
- `agents/src/improvement/crawlability.py` uses a partial home-grown robots parser, a raw word-count heuristic for JavaScript accessibility, one synthetic user-agent request as proof of CDN behavior, and shallow sitemap/meta checks.
- `agents/src/improvement/pipeline.py` treats the arbitrary structural score as a card trigger and sends only the first 3,000 characters of page text to the LLM for ready-to-paste changes.
- `page_citation_scores`, dashboard types, and the run-detail UI persist and summarize the old 0–100 model.

Therefore the cards are not mysterious AI decisions. The application first makes unsupported rule-based decisions, then prompts AI to fill in a requested fix. The new design removes that causal path.

## Goals

1. Produce repeatable, evidence-backed technical observations across Squarespace, WordPress, Webflow, and repository/deployment-managed sites.
2. Make every non-pass result operationally understandable to non-expert admins.
3. Distinguish a confirmed problem from a judgment call, unavailable integration, and irrelevant check.
4. Prevent unsupported or visually damaging changes.
5. Preserve implementation assistance without allowing a finding to directly become a production mutation.
6. Keep the system small enough for two non-specialist founders to operate confidently.

## Non-goals

- A universal GEO/readiness score.
- An agent swarm, microservices, user-authored rule language, or dynamic rules builder.
- Guaranteed AI-crawler access based only on a synthetic request.
- Automatic source discovery or content rewriting in v1.
- Automatic production publishing, repository merging, or destructive plugin/theme changes.
- Enforcing every SEO convention as a pass/fail requirement when search engines treat it as optional or contextual.

## Product Model

### Statuses

| Status | Meaning | Admin action |
|---|---|---|
| `pass` | The check was applicable, completed, and met its rule. | None. Evidence remains inspectable. |
| `fail` | A deterministic defect or supported contradiction was confirmed. | Resolve using the supplied safe remediation path. |
| `review` | Evidence exists, but correctness or intent requires bounded judgment. | Answer a plain-language question or review a staged draft. |
| `unknown` | The system could not complete an applicable check. | Follow the named unblock step, such as connecting Search Console or retrying a blocked URL. |
| `not_applicable` | The rule does not apply to this page/site/configuration. | None. The applicability reason explains why. |

`unknown` never means “probably fine,” and `not_applicable` never lowers a score because there is no score.

Examples of `unknown` include Search Console coverage when it is not connected, Bing submission when it is in scope but its integration is not connected, a source returning 403 to the auditor, or a page-speed field check with insufficient CrUX data. Examples of `not_applicable` include Article author rules on a contact page, an LCP-image lazy-loading rule when the LCP is text, FAQ validation on a page with no FAQ/schema, or `llms.txt` when the client has not opted in and the platform cannot serve a root file.

### Resolution contract

Every `fail`, `review`, or `unknown` result must contain:

- what was checked and on which URLs;
- observed evidence and retrieval time;
- expected condition and why it applies;
- confidence and whether judgment is involved;
- a single next action;
- who can resolve it (`system`, `admin`, `client`, or `integration`);
- implementation availability (`draftable`, `staged`, `guided`, or `unavailable`);
- verification procedure after resolution.

This contract is the main safeguard against founders seeing a status without knowing what to do.

## Architecture

```text
Client profile + target queries + production domain
                         │
                         ▼
                 Site inventory builder
      raw/rendered HTML, headers, URLs, links, assets,
       robots, sitemaps, TLS, performance observations
                         │
                         ▼
             Versioned deterministic check registry
     applicability → evaluate → evidence → status → next action
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
       Audit results/finding       Review queue
       lifecycle and grouping      bounded AI assistance
               │                   │
               └─────────┬─────────┘
                         ▼
               Remediation catalogue
                         │
          adapter + stale-state guard + preview
                         │
                         ▼
              explicit approval → apply → re-audit
```

The implementation remains a modular monolith. Checks are independent registry entries, but share crawled observations to avoid repeated fetching.

### Shared observations

The inventory layer records raw and rendered observations once:

- canonical request URL, final URL, redirect chain, status, MIME type, headers, retrieval time, and content fingerprint;
- raw HTML and browser-rendered DOM fingerprints, with extracted head/body fields;
- title, meta description, canonical, robots directives, visible headings/dates/bylines, and structured data blocks;
- internal/external links, anchors, images, responsive candidates, dimensions, bytes, and load behavior;
- robots and sitemap documents with their source URLs;
- TLS certificate and HTTP-to-HTTPS behavior;
- Lighthouse/CrUX provenance when available;
- platform and integration provenance.

Raw artifacts should use bounded retention and access controls. Results store excerpts/fingerprints rather than unnecessary copies of whole sites.

### Check contract

Each versioned check has stable semantics:

```python
CheckDefinition(
    id="canonical.target_health",
    version=1,
    section="canonical_url",
    severity="high",
    scope="page",
    dependencies=("page.head", "http.fetch"),
    applicable=applicability_function,
    evaluate=deterministic_evaluator,
    remediation_id="canonical.correct_target",
)
```

Each result contains:

```json
{
  "check_id": "canonical.target_health",
  "check_version": 1,
  "subject": "https://example.com/page",
  "status": "fail",
  "severity": "high",
  "summary": "Canonical target redirects",
  "expected": "The canonical target resolves directly to an indexable 200 URL",
  "observed": {"canonical": "…", "status": 301, "final_url": "…"},
  "evidence_refs": ["observation-id"],
  "scope": {"sampled": false, "urls_checked": 1},
  "applicability": {"applies": true, "reason": "canonical link is present"},
  "confidence": "high",
  "next_action": {"owner": "admin", "instruction": "…"},
  "remediation_id": "canonical.correct_target"
}
```

Rules are changed by adding a new version, not silently changing historical interpretation.

### Scope and applicability

The audit starts from:

1. query-matched pages and client-declared priority pages;
2. homepage, primary navigation, services/products, conversion pages, and content templates;
3. sitemap and internal-link discovery;
4. a full crawl for small sites, or explicit representative/template sampling for large sites.

Every section defines applicability before evaluation. Missing business information is not automatically an error. For example, Article schema cannot truthfully require an author that the website does not identify; the system returns `review` for the coverage decision or `not_applicable` when the page is not editorial. It never invents an author.

### Verified client profile

A short, reusable profile holds facts the public website cannot reliably establish:

- legal/brand name, preferred domain, public locations, and contact information;
- platform, repository, deployment provider, active theme/plugins, and implementation mode;
- which pages are editorial, services, products, locations, private, or intentionally excluded;
- approved crawler policy and priority search engines;
- authoritative internal claims/owners and regulated-content constraints;
- analytics, Search Console, Bing, and performance integration status.

Admins prepare evidence; clients confirm business truth in plain language. Clients are not asked to choose canonical syntax, schema fields, or image formats.

## Finding Lifecycle and Presentation

A finding key combines client, check ID/version, normalized subject, and material evidence identity. Runs classify it as `new`, `continuing`, `changed`, `resolved`, or `regressed`. Shared causes are grouped—for example, one footer link error or one template title defect produces one card with affected URLs instead of dozens.

The run summary shows:

- applicable checks passed;
- confirmed failures by urgency;
- reviews needing judgment;
- unknown checks and their unblock actions;
- not-applicable checks, collapsed but inspectable;
- resolved/regressed changes from the previous run.

No total score is shown. Lighthouse's own score may appear as a clearly labelled lab diagnostic, never as the product's technical score.

## The Thirteen Audit Sections

### 1. `llms.txt`

`llms.txt` is an optional observation, not a core requirement. Absence is `not_applicable` unless the client opted in or the file is expected on a supported platform.

When applicable, deterministically verify that the root request returns the intended text/Markdown file rather than an HTML fallback, has a usable heading and description, contains no secrets or staging URLs, and links to healthy canonical pages. Semantic review checks whether the description and selected links truthfully represent the site. Do not add AI usage restrictions as a required field. Do not construct proxy infrastructure solely to force root-file support on Squarespace.

### 2. Schema markup

Separate integrity from coverage.

Integrity checks parse JSON-LD, RDFa, and Microdata from raw/rendered output; handle arrays and `@graph`; identify malformed blocks, placeholders, duplicate/conflicting entities, unhealthy URLs, and contradictions with visible content or the verified profile. A present value that matches evidence passes; a contradiction fails; an unsupported value is reviewed or failed according to risk.

Coverage checks schema only where the page genuinely supports it. Organization/WebSite may suit the homepage; LocalBusiness requires a real location/business basis; Article/BlogPosting applies only to genuine editorial content; dates must be truthful; optional email/description fields are not universal requirements. Existing FAQPage markup is checked against visible FAQs, but FAQ schema is not required or generated merely because a page has questions. Missing optional/recommended coverage is `review`, not `fail`. Never invent an author or other absent entity data.

### 3. `robots.txt`

Use an established robots parser and a versioned registry of relevant crawlers. Evaluate effective access to the homepage, query targets, priority public pages, and sitemap; do not require explicit `Allow: /`. Respect groups, longest-match precedence, wildcards, end anchors, and sitemap declarations. Private/admin paths may remain blocked.

Clients have approved the policy of allowing configured AI/search crawlers to public pages, but implementation must preserve intentional privacy rules and use minimal changes. A missing `robots.txt` that semantically allows crawling is advisory, not a failure; an HTML fallback or malformed effective policy is a defect. Synthetic crawler requests are supporting evidence only—logs/WAF integrations are needed to confirm real delivery behavior.

### 4. Sitemap

Discover conventional and robots-declared sitemap URLs, parse sitemap indexes and children, and validate XML/UTF-8, absolute URLs, host/scope, and protocol limits. Check each in-scope entry for direct health, indexability, canonical consistency, and robots compatibility. Redirects/404s are defects; 403/429/transient blocks are `unknown` until confirmed.

“Key pages” means query targets, client priorities, and primary-navigation canonical pages. Omission of these pages fails when the site relies on a sitemap; omission of other discovered pages is reviewed. `lastmod` is optional, but when present it must be valid, not future-dated, and credible. Search Console and Bing submission/processing are separate integration checks: disconnected but in-scope integrations are `unknown`; deliberately out-of-scope services are `not_applicable`. Fix source page settings on platforms such as Squarespace rather than editing generated XML.

### 5. SSL and HTTPS

Check valid chain, hostname, validity period, canonical HTTPS variants, HTTP-to-HTTPS redirects, loops/wrong destinations, and browser-observed mixed content. More than 30 days to expiry passes; 8–30 days is `review`; seven days or fewer fails urgently; expired is critical. An ordinary HTTP hyperlink is not mixed content.

Do not add broad TLS/cipher grading, Certificate Transparency, OCSP, or mandatory HSTS to v1. Use platform/host controls. Never blindly replace every `http://` string, and require business review before removing an insecure embedded integration.

### 6. Meta title

Verify exactly one nonempty title in the document head for applicable pages, detect malformed titles and exact duplicates among canonical indexable pages, and review near-duplicates. Character count is triage, not correctness: under roughly 65 gets no length warning, 65–100 is reviewed if verbose, and over 100 is reviewed; length alone never fails.

Semantic review covers accuracy, title/H1 relationship, stale dates, language, and stuffing. AI may draft from visible content and verified brand/service/location facts only. On Squarespace and similar platforms, editing an SEO title must not silently change the visible H1.

### 7. Meta description

Priority canonical indexable pages should have one nonempty description. Priority includes homepage, query targets, services/products, conversion pages, and high-traffic pages. Missing descriptions on lower-priority content are reviewed because search engines may generate snippets. Exact duplicates are deterministic; near-duplicates require review.

Use length only for triage: below 50 or above 200 characters is reviewed, while 50–200 creates no automatic issue. Accuracy, unsupported claims, stale dates, language, and keyword lists require evidence-based review. Redirects, private/non-HTML pages, canonical duplicates, and intentionally noindex/nosnippet pages can be `not_applicable`. Preview social metadata side effects before publishing.

### 8. Canonical URL

Check for conflicting declarations, source/rendered/header consistency, absolute HTTPS URLs without fragments, healthy direct targets, redirect/canonical chains, staging/unrelated targets, and consistency with sitemap/internal links/hreflang. Missing canonicals are recommended rather than universally required.

Preferred self-canonicals suit unique pages; duplicate variants should point to the preferred page. Determine preference from verified domain, CMS permalink, redirects, explicit canonical, sitemap, internal links, and content clusters. Conflicting evidence is `review`, not an AI decision. Unexpected cross-domain canonicals are critical. Search Console's user/Google canonical comparison is `unknown` when its integration is absent without making the base canonical check unknown.

### 9. Source citations

Remove universal link-count rules. A page needs support for externally verifiable claims that reasonably require it; the count follows the claims. In v1, audit existing citation links and identify important unsupported claims, but do not discover or insert new sources automatically.

Map atomic claims to exact retrieved evidence passages and compare number, entity, date, geography, unit, and meaning. A healthy source that directly supports the claim passes; dead, contradictory, or unrelated evidence fails; partial/paraphrased/high-risk/stale support is reviewed; access blocks are `unknown`; pages with no external factual claims are `not_applicable`. Prefer original government/regulator/dataset/standards/research/professional sources, then reputable secondary reporting. A credible domain alone does not prove a sentence.

Store publisher, publication/update/retrieval dates, canonical URL, evidence passage, fingerprint, and claim mapping. AI may extract claims and compare supplied passages, but cannot invent a URL, infer authority from a domain suffix, cite an unretrieved page, or finalize ambiguous high-risk claims.

Any citation draft must preserve the site's visual system. Link the relevant human-readable words or source name using the platform's normal editor; do not paste a long raw URL into visible copy unless that is already the site's deliberate citation style. Preview the affected page before approval.

V2 may add safe source discovery: atomic claim → real search/scholarly API → retrieve exact page → reject unsafe/unrelated/stale results → prefer original source → extract passage → constrained comparison → human review → staged draft. All retrieval must enforce SSRF protections, redirect validation, time/size limits, and private-network denial.

### 10. Freshness signals

Remove the universal 90-day rule and never change a date without a meaningful content update. Classify pages as dated editorial, time-sensitive operational, or timeless/utility.

For applicable pages, verify visible/schema/metadata dates are valid, nonfuture, ordered (`dateModified >= datePublished`), and reasonably consistent; sitemap `lastmod` is supporting evidence. Dates must refer to the page update, not merely an event described on it. CMS, Git, and HTTP timestamps are supporting signals rather than proof of a content change.

Detect evidence of staleness such as expired events, old years presented as current, superseded sources, outdated “current” rates, schema/visible-date conflicts, or availability contradictions. Review schedules are reminders, not factual failures. When history is absent, return `unknown` for change verification and establish a baseline. Ignore footer, styling, analytics, copyright-year, and trivial typo changes when identifying a meaningful update.

### 11. Broken links

Inventory raw/rendered links across content, navigation, footer, images, downloads, and fragments. Normalize and deduplicate destinations, use bounded concurrency, GET fallback, redirects, retries, browser verification where needed, and safe retrieval controls.

Confirmed internal/external 404/410, repeated 5xx, soft-404, DNS/TLS failures, loops, wrong destinations, and broken fragments fail. Expected redirects pass; unnecessary internal redirects or changed-but-related destinations are reviewed. 403/429/transient/auth/paywall/geo-blocked results are `unknown`. `mailto`, `tel`, `sms`, logout, and admin actions are generally `not_applicable`. Group shared-component failures. Never delete a link by default; prefer typo repair, current equivalent, redirect repair, re-sourcing, and only then reviewed removal.

### 12. Image optimization

Do not require nonempty alt text for every image, cap alt text at an arbitrary character count, enforce fixed byte limits, or mandate WebP. Verify successful load/decode, MIME/fallback behavior, HTTPS, aspect ratio, responsive candidates, reserved dimensions, appropriate resolution, and duplicate downloads.

Every content image needs an `alt` attribute; informative images need meaningful alt text, while decorative images need `alt=""`. Filenames, URLs, and stuffing are invalid. Linked-image alt should describe link purpose, and complex graphics may need nearby explanation. Decorative-versus-informative is contextual: AI vision may propose a classification/draft but uncertain identity, medical, location, and product facts remain `review`.

Evaluate measured bytes, dimensions, savings, and user impact rather than fixed limits. Format depends on content and must preserve transparency, animation, sharpness, and color. The actually measured LCP image should not be lazy-loaded and should be discoverable early; if LCP is text, that check is `not_applicable`. Respect platform-native responsive/WebP delivery and preview desktop/mobile output before approval.

### 13. Page speed

Field data is primary and lab data is diagnostic. At the 75th percentile:

| Metric | Pass | Review | Fail |
|---|---:|---:|---:|
| LCP | ≤ 2.5 s | > 2.5–4.0 s | > 4.0 s |
| INP | ≤ 200 ms | > 200–500 ms | > 500 ms |
| CLS | ≤ 0.1 | > 0.1–0.25 | > 0.25 |

Use page-level CrUX first and label origin-level data separately. Insufficient field data is `unknown`, not failure. Lab testing uses the median of three controlled mobile runs. Lighthouse Performance 90+ is a passing lab target, 50–89 is review, and below 50 fails the lab check, but it is displayed as an external diagnostic. Lab cannot pass INP; TBT is only a diagnostic proxy.

Record URL, device, date, region, Lighthouse version, throttling, cache state, consent/auth state, and median. Audit all priority pages on small sites and representative query/conversion/template/high-traffic/heavy pages on large sites. Generate root-cause findings (LCP phases, shifting elements, main-thread/interaction causes), grouped across templates. Never automatically remove analytics, consent, booking, payment, accessibility, fonts, scripts, or layout behavior.

## AI Boundary

AI must not determine HTTP status, tag existence, JSON parseability, URL equality, date equality, certificate expiry, measured dimensions/bytes, or performance thresholds. Ordinary software does this through HTTP/TLS clients, parsers, a real browser, link checkers, image metadata, and official APIs. The founders do not manually calculate these facts.

AI may:

- classify a page or image when deterministic evidence is incomplete;
- compare visible content with schema or a retrieved source passage;
- group semantically similar findings;
- explain a technical result in plain language;
- draft a bounded fix from an approved evidence map.

Every AI output is schema-validated, carries input evidence references and model/prompt versions, and is either `review` or a draft. Failure to parse is an error, never empty “safe” content. AI cannot elevate its own output to `pass`, approve a factual claim, or publish.

## Remediation and Implementation

Audit results and changes are separate records. A finding references a remediation catalogue entry that defines prerequisites, risk, supported adapters, patch builder, validators, preview requirements, approval policy, rollback, and post-apply re-audit.

### Modes

- `draftable`: produce exact proposed values/diff but make no external change.
- `staged`: create a branch, CMS draft, staging change, or preview.
- `guided`: provide platform-specific instructions and copy-ready values when no safe API exists.
- `unavailable`: explain the missing adapter/permission without hiding the audit finding.

### Safety contract

Before applying any change:

1. Re-fetch the target and compare its current fingerprint/value with the audited precondition.
2. Refuse stale or conflicting changes.
3. Build the smallest possible diff through the platform's authoritative control.
4. Validate syntax, links/schema, build output, and policy constraints.
5. Produce a visual/functional preview where presentation or behavior can change.
6. Require explicit approval for production-impacting changes.
7. Retain rollback information.
8. Re-audit the production URL and mark the finding resolved only from evidence.

Content, citations, business facts, analytics/consent, structural layout, and risky integrations are never auto-approved. Even deterministic metadata/schema changes begin staged in v1.

### Platform adapters

The audit always examines the production URL and is platform-independent. Implementation uses a thin adapter selected from a one-time connection profile.

- **GitHub/repository:** create a branch and minimal diff, run tests/build, create a preview and pull request, and never auto-merge in v1. The deployment-provider adapter separately handles domains, redirects, certificates, and environment behavior.
- **WordPress:** detect the authoritative theme/plugin/core setting, use least-privilege Application Passwords where appropriate, write drafts/staging changes, and fall back to guided mode when ownership is ambiguous.
- **Webflow:** use scoped APIs for supported metadata/CMS operations, stage or publish individual pages only after approval, and treat global custom code cautiously.
- **Squarespace:** prefer native settings and guided/copy-ready changes. Do not manufacture unsupported root-file or source-code write access.

An unavailable adapter never changes a `fail` to `unknown`; implementation availability is a separate field.

## Data and Migration Design

Introduce a new versioned technical-audit result model rather than mutating `page_citation_scores` into a different meaning:

- `technical_audit_runs`: audit version, status, scope summary, observation/check counts, integration state, timestamps, and linked improvement/pipeline run.
- `technical_audit_results`: check identity/version, subject, status, severity, summary, expected/observed JSON, evidence references, applicability, scope, confidence, next action, remediation ID, and lifecycle state.
- `audit_observations`: typed bounded evidence with provenance, retrieval time, fingerprint, and artifact reference.
- `remediation_drafts`: finding link, adapter/mode, audited precondition, proposed patch/instructions, validation/preview/approval/apply/rollback/re-audit state.
- `client_site_profiles`: verified facts, platform connections, policy, priorities, and integration states.

Do not delete historical `page_citation_scores` or action cards. Old runs remain readable and are labelled **Legacy readiness score**. New runs write checklist results and no longer use the structural score to generate technical cards. The existing content-gap/community workflow may continue independently, but its broad AI-generated content brief must be reviewed under a separate content design before production use.

During migration:

1. Add new tables/types and read paths without changing old run rendering.
2. Implement the new audit behind `technical_audit_version = 1` for test clients.
3. Render a checklist summary for new runs; route old runs to the legacy view.
4. Remove technical calls from `compute_structural_score → classify_actions → generate_sonnet_specifics` in the new path.
5. Disable auto-approval for all new remediation drafts until adapter-specific evidence proves safety.
6. After parallel validation, make v1 the default and retain a bounded rollback flag.

## Delivery Sequence

The system is delivered incrementally without changing the approved end-state:

1. **Foundation:** schema, status/result contract, client profile, inventory/evidence layer, lifecycle, and checklist UI.
2. **Core protocol checks:** `llms.txt`, schema integrity, robots, sitemap, HTTPS, meta, and canonical.
3. **Site-wide checks:** links, images, freshness, source-support audit, and page speed/integrations.
4. **Remediation safety:** catalogue, draft/stage/guided state machine, GitHub/WordPress/Webflow/Squarespace adapters, preview, approval, rollback, and re-audit.
5. **Controlled rollout:** fixture sites, test client, shadow comparison, failure review, then default-on.

The production release should not call a partial subset “complete.” Sections without their required integration/evidence return explicit `unknown`, and the UI names the unblock action.

## Testing and Operational Quality

### Deterministic fixtures

Maintain local fixture sites/pages for each status and ambiguity case, including malformed/duplicate schema, robots precedence, sitemap indexes, redirects/soft-404s, conflicting canonicals, mixed content, decorative/informative images, stale date contradictions, inaccessible sources, and pages with no applicable rules.

### Test layers

- unit tests for applicability and every check outcome;
- contract tests for observation/result schemas and version stability;
- parser conformance tests, especially robots/sitemap/schema;
- integration tests with mocked HTTP/browser/Search Console/CrUX/platform APIs;
- adversarial retrieval tests for SSRF, redirects, oversized content, malformed MIME, and prompt injection in page/source text;
- adapter tests for stale-precondition refusal, least privilege, minimal diff, preview, rollback, and re-audit;
- visual regression and accessibility checks for presentation-affecting remediations;
- golden tests ensuring AI never adds unsupported facts/URLs/dates and cannot change status.

### Run observability

Record check version, dependency result, duration, retries, bytes/pages sampled, integration provenance, and structured error class. Monitor unknown-rate changes, review backlog, repeated/transient failures, false-positive reversals, adapter refusal reasons, and regressions after implementation. Never log secrets or full credential-bearing URLs.

## Acceptance Criteria

1. The same observations and rule versions produce the same deterministic statuses.
2. Every result has evidence, applicability, scope, and a useful resolution path.
3. No new technical action is triggered by a proprietary score.
4. Missing integrations and irrelevant rules are visibly distinguished.
5. The system cannot generate a citation URL it did not retrieve or a factual field unsupported by evidence/profile.
6. A finding cannot directly publish a change; stale-state guard, validation, approval, and re-audit are enforced.
7. Platform limitations affect implementation mode, not audit truth.
8. Historical runs remain readable and clearly labelled legacy.
9. The checklist handles ambiguous sites through evidence hierarchy and `review`, without asking clients technical implementation questions.
10. The dashboard groups shared causes and gives the founders one clear next action for every non-pass result.

## Primary References

- Google Search Central: [robots.txt introduction](https://developers.google.com/search/docs/crawling-indexing/robots/intro), [build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap), [title links](https://developers.google.com/search/docs/appearance/title-link), [snippets](https://developers.google.com/search/docs/appearance/snippet), [canonical consolidation](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [publication dates](https://developers.google.com/search/docs/appearance/publication-dates), [crawlable links](https://developers.google.com/search/docs/crawling-indexing/links-crawlable), and [structured data](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data).
- Web performance: [Core Web Vitals thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds), [lab and field data](https://web.dev/articles/lab-and-field-data-differences), [Lighthouse/PageSpeed API](https://developers.google.com/speed/docs/insights/v5/about), and [LCP optimization](https://web.dev/articles/optimize-lcp).
- Accessibility/images: [W3C decorative images](https://www.w3.org/WAI/tutorials/images/decorative/), [Google Images guidance](https://developers.google.com/search/docs/appearance/google-images), and [browser lazy loading](https://web.dev/articles/browser-level-image-lazy-loading).
- Security and transport: [Chrome security inspection](https://developer.chrome.com/docs/devtools/security), [MDN mixed content](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Mixed_content), and [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
- Source metadata/research: [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) and the original [Generative Engine Optimization paper](https://arxiv.org/abs/2311.09735). The paper does not justify a universal “three citations” threshold.
- Platform controls: [WordPress REST API](https://developer.wordpress.org/rest-api/), [WordPress Application Passwords](https://developer.wordpress.org/advanced-administration/security/application-passwords/), [Webflow API scopes](https://developers.webflow.com/data/reference/scopes), [Webflow page metadata](https://developers.webflow.com/designer/set-page-metadata), [GitHub pull requests](https://docs.github.com/en/rest/pulls/pulls), [Squarespace sitemaps](https://support.squarespace.com/hc/en-us/articles/206543547-View-your-site-map), and [Squarespace SSL](https://support.squarespace.com/hc/en-us/articles/205815898-Understanding-SSL-certificates).
