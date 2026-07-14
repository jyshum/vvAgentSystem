# V1 Simplification and Technical Audit Expansion

**Status:** Approved

**Date:** 2026-07-14

**Builds on:** `2026-07-14-deterministic-technical-audit-design.md`

## Purpose

Simplify the V1 product around three trustworthy capabilities:

1. AI visibility for tracked queries;
2. deterministic technical website auditing;
3. bounded manual community-research opportunities.

The product will stop presenting heuristic query-to-page coverage as fact. It
will preserve historical runs and reuse the neutral crawling infrastructure,
while expanding the deterministic checklist through independently testable
check sets.

The detailed rules in the original deterministic technical-audit design remain
normative. This specification changes product scope, orchestration,
presentation, rollout, and implementation workflow; it does not weaken those
rules.

## Product Scope

### Active V1 tracks

New V1 runs contain three independent tracks:

```text
AI visibility
  tracked queries, client mentions, competitor mentions

Technical audit
  bounded production evidence -> deterministic checks -> unified audit cards

Community research
  at most five manual opportunities from the largest measured competitor leads
```

### Deferred for new V1 runs

New V1 runs do not execute or present:

- query and page embedding comparison;
- similarity scores;
- `matched`, `weak`, or `content_gap` classifications;
- structural/citation-readiness scores;
- inferred content-gap briefs;
- competitive-gap action cards;
- AI-generated technical fixes from the legacy structural scorer.

The neutral page inventory and evidence collectors remain. Crawling a page is
not the same as semantically scoring its relationship to a query.

### Preserved legacy behavior

- Historical matching, scoring, cards, and tables are not deleted or
  reinterpreted.
- Historical run URLs continue to render their original evidence with a clear
  `Legacy` label.
- The Pages tab is removed from primary navigation for V1, but its route and
  historical data remain available.
- Rollback must not require restoring deleted data.

## Dependency Cleanup

The current community workflow is accidentally coupled to page matching:

```text
page matches -> competitive-gap helper -> community card
```

It will instead consume tracker visibility evidence directly:

```text
tracked query visibility -> measured client/competitor rates
  -> top five competitor-leading queries -> manual community opportunities
```

Competitor mention-rate data remains part of AI visibility. Page-based
prioritization and competitive-gap action cards do not.

Community selection is deterministic: include only positive measured gaps,
sort descending by gap, break ties by stable query ID, and take at most five.
Do not use page relevance, an LLM, or a hidden quality score. These cards
contain search links and manual guidance; they do not claim that the system has
retrieved or validated a live community thread.

The technical audit already runs before page matching and does not consume
similarity scores. Its crawl seeds change from query-matched pages to:

- homepage;
- client-declared priority URLs;
- primary navigation pages;
- representative sitemap pages;
- representative service, product, conversion, editorial, and template pages.

## Unified Audit Card

### One operational object

Founders and clients see one card, not separate “result” and “action” objects.
Every technical check is presented as a unified audit card containing:

- status and concise title;
- subject page/site/integration;
- what was checked;
- what was observed;
- why the rule applies;
- scope and sampling disclosure;
- confidence and provenance;
- recommended outcome;
- platform implementation mode;
- proposed draft or instructions when available;
- approval/application state;
- re-audit verification state.

The implementation remains safe internally:

- immutable observation and result records preserve audit truth;
- an editable workflow record references the originating result(s);
- editing, approving, rejecting, or applying a proposed action never mutates
  the original evidence;
- the UI composes those records into one card so operators do not have to parse
  the distinction.

### Alternatives considered

1. **One mutable database row for evidence and action.** Rejected because an
   approval edit could rewrite audit history and grouping would duplicate
   evidence.
2. **Results only, with a separate implementation screen.** Rejected because
   founders would have to translate findings into work manually.
3. **One composed card over linked immutable evidence and editable workflow.**
   Selected because it provides one operational object without sacrificing
   provenance or re-audit safety.

### Status behavior

| Audit status | Card behavior |
|---|---|
| `pass` | Collapsed; states that no action is required. |
| `fail` | Open; marked Needs action with evidence and remediation path. |
| `review` | Open; asks one bounded plain-language decision and can prepare an action after approval. |
| `unknown` | Open; explains the retry, access, or integration unblock step. |
| `not_applicable` | Collapsed; explains why the rule does not apply. |

The audit page shows every card. The action inbox shows only actionable Fail,
Review, Unknown, and community cards. Shared/template defects are grouped when
the remediation is identical, while per-subject evidence remains inspectable.

### Lifecycle

```text
Observed -> Draft prepared -> Admin review -> Approved -> Applied
  -> Re-audited -> Verified or Still failing
```

Rules:

- no technical change is automatically approved or published;
- the current production fingerprint/state is checked immediately before a
  change is applied;
- stale cards cannot apply an outdated draft;
- verification always comes from a fresh deterministic check;
- a card becomes Verified only when the relevant check passes;
- authored content is drafted only from visible page content and verified
  client facts, and remains subject to human approval.

## Platform Implementation Modes

The card shape is universal; execution is platform-specific.

| Platform | V1 implementation mode |
|---|---|
| Squarespace | Guided instructions and copy-ready values/code. |
| GitHub/repository | Pull request with previewable diff. |
| WordPress | Staged/API update only where the authoritative field and rollback are supported. |
| Webflow | Staging/API update only where supported. |
| Unknown/unsupported | Guided copy/paste. |
| Community research | Manual search, review, and note-taking. |

### Squarespace safety

Squarespace is not treated as a generic source-code CMS. The audit remains
platform-independent, but remediation uses native settings:

- SEO title and description instructions target the SEO fields, not visible
  page or navigation titles;
- generated sitemap XML is never edited; the underlying page visibility,
  canonical, slug, domain, or indexability setting is corrected;
- SSL/domain findings route to Squarespace SSL/domain controls;
- schema uses guided code injection only when the plan and page scope support
  it;
- robots behavior uses available Squarespace crawler controls rather than a
  fabricated file editor;
- unsupported root-file behavior such as `llms.txt` remains optional or not
  applicable unless explicitly expected.

The system does not store Squarespace passwords, simulate editor clicks, or
claim unsupported API write access.

Existing legacy CMS adapters are not automatically considered safe for this
workflow. In particular, a legacy adapter that writes directly to production
without preview, field-level authority, rollback, and stale-state protection
must remain disabled until it satisfies this specification.

## Bounded Audit Scope

Internal V1 auditing fetches at most 20 pages per run.

Selection order:

1. homepage;
2. configured priority URLs;
3. primary navigation pages;
4. representative sitemap URLs;
5. representative page/template types for remaining slots.

Every result records:

- whether the scope was sampled;
- URLs/documents discovered;
- URLs/documents checked;
- truncation or safety caps reached;
- retrieval time and provenance.

The interface must never imply full-site coverage when a sample was used.
Large sitemaps, links, images, schema blocks, rendered documents, and response
bodies use explicit count/byte/concurrency/time limits. Reaching a limit is
evidence and produces a scoped result or Unknown state, never an unqualified
Pass.

## Versioned Check Sets

The registry exposes four check sets. Each run stores the enabled set names and
the exact check versions.

### `foundation`

Already implemented:

- optional `llms.txt` integrity;
- meta-title integrity;
- meta-description integrity;
- canonical declaration integrity.

Existing limitations remain visible until their follow-on checks land. For
example, canonical target health is not implied by a declaration-only pass.

### `protocol`

#### Robots.txt

- retrieve and validate a real text response rather than an HTML fallback;
- parse with established robots semantics: groups, longest match, wildcards,
  end anchors, and sitemap declarations;
- evaluate effective access for configured AI/search crawlers against the
  homepage and sampled public priority pages;
- preserve intentional private/admin exclusions;
- do not require an explicit `Allow: /`;
- treat a missing file that semantically allows crawling as advisory, not a
  defect;
- distinguish malformed policy from blocked/transient access;
- treat synthetic crawler requests as supporting evidence rather than proof of
  real WAF/CDN delivery.

#### Sitemap

- discover conventional and robots-declared sitemap locations;
- parse XML, sitemap indexes, and bounded child documents;
- validate encoding, absolute URLs, host, scheme, and protocol limits;
- verify priority-page coverage;
- sample entry health, directness, robots compatibility, indexability, and
  canonical consistency;
- fail confirmed redirects/404s where direct sitemap targets are required;
- return Unknown for 403/429/transient access;
- validate `lastmod` only when present; it is optional, nonfuture, syntactically
  valid, and treated as supporting evidence;
- leave Search Console and Bing submission to integration checks;
- remediate generated sitemaps through authoritative page/platform settings,
  not by editing generated XML.

#### SSL and HTTPS

- validate certificate chain, hostname, validity period, and canonical HTTPS
  variants;
- inspect HTTP-to-HTTPS redirects, loops, and wrong destinations;
- inspect browser-observed mixed content on sampled pages;
- treat an ordinary HTTP hyperlink as distinct from mixed active/page content;
- pass expiry beyond 30 days, Review at 8–30 days, Fail at seven days or fewer,
  and urgent Fail when expired;
- exclude broad cipher grading, Certificate Transparency, OCSP, and mandatory
  HSTS from V1;
- never blindly replace all `http://` strings or remove business integrations
  without review.

#### Schema integrity and coverage

- parse JSON-LD, RDFa, and Microdata from available raw/rendered evidence;
- support arrays and `@graph`;
- detect malformed blocks, placeholders, duplicates, conflicts, unhealthy
  URLs, and contradictions with visible/verified facts;
- separate integrity from coverage;
- require Organization/WebSite, LocalBusiness, Article/BlogPosting, FAQPage,
  dates, authors, and locations only when applicability evidence supports them;
- treat missing optional/recommended coverage as Review rather than Fail;
- compare existing FAQ schema with visible FAQs but never require FAQ schema
  merely because a page contains questions;
- never invent an author, location, date, organization fact, or other entity;
- return Review where page purpose or factual support remains ambiguous.

### `site_integrity`

#### Broken links

- inventory raw/rendered content, navigation, footer, image, download, and
  fragment links;
- normalize and deduplicate destinations;
- use bounded concurrency, retries, GET fallback, redirect inspection, and
  browser verification where required;
- fail confirmed internal/external 404/410, repeated 5xx, soft 404, DNS/TLS
  failures, redirect loops, wrong destinations, and broken fragments;
- pass expected redirects and Review unnecessary internal redirects or
  changed-but-related destinations;
- return Unknown for 403/429/transient/auth/paywall/geo-blocked results;
- mark `mailto`, `tel`, `sms`, logout, and admin actions Not Applicable;
- group shared-component failures;
- prefer repair/current equivalent/redirect/re-sourcing before reviewed link
  removal.

#### Image integrity and optimization

- verify load/decode, MIME/fallback, HTTPS, intrinsic/rendered dimensions,
  aspect ratio, responsive candidates, reserved space, appropriate resolution,
  duplicate downloads, measured savings, and user impact;
- preserve transparency, animation, sharpness, and color requirements;
- require an `alt` attribute for content images;
- require meaningful alt text for informative images and `alt=""` for
  decorative images;
- reject filenames, URLs, and stuffing as alt text;
- describe linked-image purpose and identify complex graphics needing nearby
  explanation;
- allow AI to propose classification or wording but require Review for
  uncertain identity, medical, location, or product facts;
- identify the measured LCP image and ensure it is not lazy-loaded; mark this
  Not Applicable when LCP is text;
- respect platform-native responsive/format delivery;
- reject universal byte caps and mandatory WebP.

#### Freshness

- classify dated editorial, time-sensitive operational, and timeless/utility
  pages;
- compare visible, schema, metadata, sitemap, CMS, Git, and HTTP date signals
  according to their evidentiary strength;
- validate nonfuture dates, `dateModified >= datePublished`, and reasonable
  consistency;
- detect expired events, superseded sources, outdated “current” rates, and
  availability contradictions;
- distinguish a page-update date from an event date mentioned on the page;
- return Unknown and establish a baseline when meaningful history is absent;
- ignore copyright years, analytics/style changes, and trivial edits;
- use review schedules as reminders rather than factual failures;
- never apply a universal 90-day rule or change a date without a meaningful
  content update.

#### Existing source support

- audit existing citations and important unsupported claims; do not discover
  or insert new sources automatically in V1;
- extract atomic claims and retrieve the exact linked evidence safely;
- compare entity, number, unit, date, geography, and meaning;
- pass direct support, fail dead/unrelated/contradictory support, Review
  partial/paraphrased/stale/high-risk support, return Unknown for blocked
  evidence, and mark pages without external factual claims Not Applicable;
- prefer original government, regulator, dataset, standard, research, or
  professional sources before secondary reporting;
- store publisher, publication/update/retrieval dates, canonical URL, exact
  passage, claim mapping, and fingerprint;
- never infer support from domain reputation alone, cite an unretrieved page,
  or let AI finalize ambiguous high-risk claims;
- preserve the site's visible citation style and avoid raw visible URLs unless
  that style is intentional.

Safe discovery of new sources remains a later V2 capability.

### `performance`

#### Core Web Vitals field evidence

Use 75th-percentile CrUX data with page-level evidence preferred and origin
fallback clearly labelled:

| Metric | Pass | Review | Fail |
|---|---:|---:|---:|
| LCP | <= 2.5 s | > 2.5–4.0 s | > 4.0 s |
| INP | <= 200 ms | > 200–500 ms | > 500 ms |
| CLS | <= 0.1 | > 0.1–0.25 | > 0.25 |

Insufficient field data is Unknown. Record scope, device, collection period,
and retrieval provenance.

#### Lighthouse lab diagnostics

- use the median of three controlled mobile runs;
- record URL, date, region, Lighthouse version, throttling, cache, consent, and
  authentication state;
- show Lighthouse's own score as an external diagnostic, never the product's
  aggregate score;
- treat 90–100 as Pass, 50–89 as Review, and below 50 as Fail for the lab check;
- do not use lab data to pass INP; TBT is diagnostic only;
- identify LCP phases, shifting elements, and main-thread/interaction causes;
- group template-level causes;
- never automatically remove analytics, consent, booking, payment,
  accessibility, fonts, scripts, or layout behavior.

#### Search Console and Bing

When connected and in scope, integration collectors retrieve sitemap
submission/processing, sampled indexing evidence, property scope, permissions,
timestamps, and available canonical evidence. Deterministic evaluators compare
those observations.

- disconnected but expected is Unknown;
- explicitly out of scope is Not Applicable;
- stale or insufficient integration data is Unknown;
- an unavailable integration never makes the independent public sitemap or
  canonical check Unknown.

Cards display these results; cards do not retrieve, verify, or decide them.

## AI Boundary

Ordinary software determines HTTP status, redirects, tag/file existence, JSON
or XML parseability, URL equality, date ordering/equality, certificate expiry,
measured bytes/dimensions, link health, and performance thresholds.

AI may assist only with bounded semantic work such as:

- page-purpose or image-purpose proposals;
- atomic claim extraction;
- comparison of a claim with an actually retrieved passage;
- constrained draft wording from visible content and verified facts;
- grouping or summarizing evidence.

AI cannot invent URLs, sources, authors, dates, locations, business facts,
schema entities, or measurements. Ambiguity becomes Review, not a fabricated
decision.

## Internal Rollout Controls

Incremental testing uses:

1. the global technical-audit feature flag;
2. an internal client allowlist;
3. one enabled check-set list.

Do not create an environment flag for every checkbox. A run persists the
effective controls and versions for reproducibility.

Suggested internal sequence:

1. simplify new-run orchestration and frontend;
2. decouple top-five community opportunities from page matching;
3. introduce the unified audit-card view;
4. enable `protocol` for internal clients;
5. review repeatability and evidence;
6. enable `site_integrity` internally;
7. review repeatability and evidence;
8. enable `performance` and connected integrations internally;
9. build remediation preparation and platform workflows;
10. seek separate production activation approval.

## Failure Handling

- A request failure affects its dependent checks and becomes Unknown with an
  unblock/retry action.
- A malformed schema block does not stop unrelated checks.
- A disconnected integration affects only its integration checks.
- A collector-level failure marks the audit run Error rather than fabricating
  results.
- AI visibility and community research may continue when the technical audit
  fails.
- No audit, card, integration, or adapter failure can auto-publish a change.
- Partial evidence and reached limits are disclosed in scope.

## Frontend

- Hide the Pages tab from primary navigation.
- Preserve direct historical routes and label legacy matching/scoring clearly.
- Remove matching/weak/content-gap funnel language from new runs.
- Keep query visibility and measured competitor data, but remove matched-page
  presentation from new V1 query views.
- Use the same unified card component on the audit page and in the filtered
  action inbox.
- Collapse Pass and Not Applicable cards; open Fail, Review, and Unknown.
- Do not render a proprietary total score.

## Data and Compatibility

- Preserve `query_page_matches`, `page_citation_scores`, historical
  `action_cards`, and their legacy readers.
- Reuse `action_cards` as the universal actionable inbox record for technical
  and community work, with an explicit source/type discriminator.
- Add an associative link from an actionable card to one or more immutable
  technical audit result IDs. Grouped cards therefore retain every originating
  result without copying or mutating its evidence.
- Fail and Review results create pending actionable workflow records. Unknown
  creates one only when the unblock owner is a human or integration owner;
  system-owned retry Unknowns remain on the audit page. Pass and Not Applicable
  render through the same unified card component but do not create inbox rows.
- The UI composition hides this storage distinction from operators.
- Store check-set names, registry/check versions, scope, and provenance on each
  run.
- Keep evidence bounded and access-controlled.
- Database changes are additive and reversible.

## Verification and Promotion Gate

Each check set requires:

- unit fixtures for pass, fail, review, unknown, and not-applicable behavior;
- mocked network, TLS, browser, CrUX, Search Console, Bing, and platform
  integration tests as applicable;
- clean, defective, redirected, blocked, malformed, ambiguous, oversized, and
  truncated fixtures;
- Squarespace-like generated behavior and adapter-specific tests;
- stale-state, approval, application, rollback, and re-audit verification;
- a bounded end-to-end fixture-site run;
- repeatable outcomes across reruns;
- every result resolving to stored evidence;
- accurate scope disclosure;
- founder-readable cards without requiring raw JSON;
- platform guidance matching the real CMS;
- preview validation for visible/design-sensitive changes;
- independent review with no unresolved important safety defects.

Production activation remains a separate decision after internal evidence
review. Merging code does not imply enabling check sets, applying migrations,
or publishing remediations.
