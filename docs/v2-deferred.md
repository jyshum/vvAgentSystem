# V2 / Deferred Features

Features intentionally deferred from the current build. Add items here as they come up.

## Measurement

- **Competitor citation tracking** — the tracker records which competitors are *mentioned* per AI response, but does not attribute *citations* to them. V2: parse response citation URLs against competitor domains so the queries page can show competitor citation rate alongside mention rate (answers "why are they winning," not just "who"). (2026-07-11)
- **Branded intent measurement** — branded bucket queries are stored but excluded from tracker runs and all reporting. Config UI retains the branded section for future activation.

## Scoring & matching (from 2026-07-12 design review)

- **Structural scores for all inventoried pages** — the 100-point structural score is pure HTML parsing (zero API cost) but is only computed for query-matched pages, so "not scored" conflates "no data" with "serves no tracked intent." V2: score every inventoried page structurally, label it "structural only — no target query," and reserve the LLM quality dimensions for matched pages. (2026-07-12)
- **Unmatched pages as query-discovery signal** — pages with no matching query may serve buyer intents the 8-intent set doesn't track (e.g. the disability-insurance article). V2: surface unmatched inventoried pages as query-set expansion candidates ("you have content here — should we track an intent for it?"). (2026-07-12)
- **Weak-match content briefs** — queries in the 0.3–0.5 similarity band produce no score, no card, no brief (dead zone). V2: generate a content-brief card for weak matches, same as content gaps, so every query resolves to an action: optimize page / track new intent / write new content. (2026-07-12)
- **Improvement runs should report dropped cards** — cards that fail QA twice are dropped with only a log line (e.g. add_faq_schema dropped for JSON-LD truncation on 2026-07-12 run). V2: persist a dropped-card count + reasons on improvement_runs and show it on the run page. (2026-07-12)
- **Pre-run card-gen preflight** — before a paid full run, fire one production-shaped card-generation call (~$0.02) and abort the pipeline if it fails, so model/API regressions can't burn a full tracker phase. (2026-07-12)

## Dashboard

- **Server-rendered PDF reports** — reports are currently client-rendered; server PDFs deferred.
- **GSC integration** — `gsc_site_url` is plumbed through the pipeline but no client has it configured; GSC metrics render as pending.
- **Improvement pipeline frontend** — richer views for crawlability reports, page inventory, and query-page matches beyond the current cards/runs pages.
- **All citation URLs in query drilldown** — the drilldown shows a single citation link per engine even when multiple wordings were cited with different URLs (data is stored per response in tracker_results; only one is rendered). V2: list every distinct cited URL with its wording, like mention evidence. (2026-07-12)
- **Render markdown in mention evidence** — engines (esp. Perplexity) answer with markdown tables; the evidence extractor splits on sentence punctuation and renders raw pipes/headers as one jammed plain-text line. V2: strip or render markdown in evidence sentences and truncate to a window around the brand match. (2026-07-12)
- **Cycle-aware query drilldown** — the query-detail API always reads the latest tracker run regardless of which cycle column is expanded. (2026-07-12)
