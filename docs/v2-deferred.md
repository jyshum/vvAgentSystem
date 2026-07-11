# V2 / Deferred Features

Features intentionally deferred from the current build. Add items here as they come up.

## Measurement

- **Competitor citation tracking** — the tracker records which competitors are *mentioned* per AI response, but does not attribute *citations* to them. V2: parse response citation URLs against competitor domains so the queries page can show competitor citation rate alongside mention rate (answers "why are they winning," not just "who"). (2026-07-11)
- **Branded intent measurement** — branded bucket queries are stored but excluded from tracker runs and all reporting. Config UI retains the branded section for future activation.

## Dashboard

- **Server-rendered PDF reports** — reports are currently client-rendered; server PDFs deferred.
- **GSC integration** — `gsc_site_url` is plumbed through the pipeline but no client has it configured; GSC metrics render as pending.
- **Improvement pipeline frontend** — richer views for crawlability reports, page inventory, and query-page matches beyond the current cards/runs pages.
