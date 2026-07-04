# Phase 1: Multi-Run Execution + New Scoring Model

**Date:** 2026-07-01
**Status:** Approved
**Part of:** AI Visibility Tracker Overhaul (see `AI_VISIBILITY_OVERHAUL.md`)

---

## Overview

Transforms the tracker from a single-run binary detection system into a multi-run, multi-signal measurement platform. Every prompt runs 5 times per LLM per cycle. Detection upgrades from boolean mention/citation to a 4-level mention classification. Scoring replaces the binary aggregate with two clean metrics (mention rate + avg mention level) and separates citation rate as a per-LLM contextual metric.

---

## 1. Backend — Multi-Run Execution

### tracker.py

- `run_tracker()` loops each prompt **5 times per LLM** instead of once.
- All 5 runs for a given prompt+engine fire concurrently via `asyncio.gather`.
- If any engine's parallel batch fails (rate limit, timeout), fall back to sequential for that engine and log a warning.
- Each run returns full response text + detection results, plus `run_number` (1-5).
- `runs_per_prompt` defaults to 5, configurable per client via client config.

### detection.py

- After `detect_brand()` finds a string-match mention, make one Claude Haiku API call to classify mention level (0-4).
- Classification prompt: `"How is [brand_name] positioned in this AI response? Classify as one of: passing_mention, listed_with_context, recommended, primary_recommendation. Respond with only the classification."`
- Returns enriched result: `brand_mentioned`, `brand_cited`, `citation_url`, `mention_level` (int 0-4), `mention_level_label` (string).
- If brand is not mentioned, `mention_level = 0`, `mention_level_label = "not_mentioned"` — no Haiku call needed.

### Mention Level Scale

| Level | Value | Description |
|---|---|---|
| Not mentioned | 0 | Brand doesn't appear |
| Passing mention | 1 | In a list without recommendation |
| Listed with context | 2 | Described but not endorsed |
| Recommended | 3 | AI actively recommends |
| Primary recommendation | 4 | Lead answer |

### compute_scores() rewrite

- **mention_rate** = runs where brand appeared / total runs × 100 (across all engines)
- **avg_mention_level** = sum of levels where mentioned / count of mentioned runs (not diluted by zeros)
- **per_engine_scores** = `{engine: {mention_rate, avg_mention_level, citation_rate}}` — citation rate is per-engine, not aggregated
- No more `aggregate_citation_rate` as a top-level metric.

### upload.py

- `tracker_results` rows include `run_number`, `mention_level`, `mention_level_label`.
- `tracker_runs` aggregate row stores: `aggregate_mention_rate`, `aggregate_avg_mention_level`, `per_engine_scores` (with all three metrics per engine).
- New `prompt_scores` table populated after each cycle — one row per prompt × engine with aggregated mention_rate, avg_mention_level, citation_rate.

---

## 2. Database Schema Changes

### Modified: tracker_results — add columns

| Column | Type | Description |
|---|---|---|
| `run_number` | integer | Which run (1-5) for this prompt × LLM pair |
| `mention_level` | integer | 0-4 scale |
| `mention_level_label` | text | not_mentioned, passing_mention, listed_with_context, recommended, primary_recommendation |

### Modified: tracker_runs — replace aggregate scores

| Remove | Add |
|---|---|
| `aggregate_citation_rate` | `aggregate_avg_mention_level` (numeric) |
| | `per_engine_scores` restructured to `{engine: {mention_rate, avg_mention_level, citation_rate}}` |

`aggregate_mention_rate` stays — same concept, now calculated across 5 runs instead of 1.

### New table: prompt_scores

| Column | Type | Description |
|---|---|---|
| `id` | uuid | Primary key |
| `run_id` | uuid | FK to tracker_runs |
| `client_id` | text | FK to clients |
| `query` | text | The prompt text |
| `llm` | text | Which engine |
| `mention_rate` | numeric | appearances / 5 runs × 100 |
| `avg_mention_level` | numeric | avg level across mentioned runs |
| `citation_rate` | numeric | cited runs / mentioned runs × 100 |
| `created_at` | timestamp | |

### Migration approach

Clean break. New migration adds columns and table. Old tracker_runs and tracker_results rows stay in the DB but the dashboard ignores them — the frontend queries filter by `run_number IS NOT NULL` to only show runs made under the new system. No backfill of old data.

---

## 3. Frontend — Dashboard Changes

### types.ts

- `TrackerRun`: remove `aggregate_citation_rate`, add `aggregate_avg_mention_level` (number). `per_engine_scores` shape becomes `Record<string, {mention_rate: number, avg_mention_level: number, citation_rate: number}>`.
- `TrackerResult`: add `run_number` (number), `mention_level` (number), `mention_level_label` (string).
- New `PromptScore` interface: `{query: string, llm: string, mention_rate: number, avg_mention_level: number, citation_rate: number}`.

### VisibilityOverview.tsx — KPI section (Layout C: Hero Pair + Engine Grid)

- Two hero cards: Mention Rate (green, %) + Avg Mention Level (blue, 0-4 with human-readable label).
- Below: 4-column engine grid, each card showing mention rate, avg level, citation rate.
- Delta indicators on hero cards (vs previous cycle).
- Color coding: mention rate uses existing thresholds (red/orange/yellow/green), avg level gets its own scale (0-1 red, 1-2 orange, 2-3 yellow, 3-4 green).

### TrendChart.tsx — Dual Y-axis

- Left axis: Mention Rate 0-100% (green line).
- Right axis: Avg Mention Level 0-4 (blue line).
- Same time axis, shared tooltip showing both values on hover.

### QueryResultsTable.tsx — Two-level drill-down

- Top level: query text, overall mention rate %, overall avg level label, overall citation info.
- First expand (click query row): per-engine row for each of the 4 engines showing engine-specific mention rate, avg level, citation rate.
- Second expand (click engine row): within an engine, show 5 individual runs with run_number, mention_level_label, brand_cited, response text snippet.

### KPIGrid.tsx (report view)

- Same Layout C structure as dashboard: two primary metric cards + engine grid.
- Sparklines show historical trend per metric across cycles.

### CompetitorTable.tsx

- No changes in Phase 1. Current binary competitor mention rates stay as-is. Competitor mention level enrichment comes in Phase 3.

### utils.ts

- New helper: `getMentionLevelLabel(level: number): string` — maps 0-4 to human-readable labels.
- New helper: `getMentionLevelColor(level: number): string` — maps 0-4 to color.
- Update existing score formatting functions to handle new metric shapes.
- Remove code that computes or formats `aggregate_citation_rate` as a top-level metric.

---

## 4. Graph/Pipeline Integration

### state.py — GEOState TypedDict

- `tracker_scores` shape changes to: `{mention_rate, avg_mention_level, per_engine_scores: {engine: {mention_rate, avg_mention_level, citation_rate}}}`.
- `tracker_results` list items include `run_number`, `mention_level`, `mention_level_label` per result.

### nodes.py — run_tracker_node

- No structural change. Still calls `tracker.run_tracker()` and `tracker.compute_scores()`, then `upload.upload_results()`.
- One addition: after uploading tracker_results, compute and insert `prompt_scores` aggregates.

### pipeline.py — Graph edges

- No changes. Graph shape is identical. Multi-run execution is invisible to the graph.

### server.py — API endpoints

- No changes to `/api/run`, `/api/approve`, `/api/status`.
- APScheduler triggers remain unchanged.

### output.py — Reporting

- HTML report updated to match new metrics: mention rate + avg level as primary, per-engine citation rates, per-query breakdown with level labels.
- CSV export adds `run_number`, `mention_level`, `mention_level_label` columns.
- JSON report structure mirrors new `compute_scores()` output.

---

## 5. Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Parallel vs sequential runs | Parallel-first via asyncio.gather, sequential fallback per engine on failure | Speed; rate limits are engine-specific so fallback is scoped |
| Old data migration | Clean break — no backfill | Simplicity; old binary data can't meaningfully map to new metrics |
| Citation rate display | Third KPI area, broken out per-engine | Citation behavior varies by platform; aggregating hides the signal |
| KPI layout | Hero Pair + Engine Grid (Layout C) | Two primary metrics dominate, engine grid shows all three signals in context |
| Trend chart | Dual Y-axis (mention rate left, avg level right) | Space-efficient, both signals visible on one chart |
| Query drill-down | Two-level: engine summary → individual runs | Quick checks at engine level, deep debugging at run level |
| runs_per_prompt | Default 5, configurable per client | Flexibility for clients who want more precision or cost savings |

---

## 6. Cost Impact

| Metric | Before | After |
|---|---|---|
| API calls per cycle per client | 80 (20 prompts × 4 LLMs × 1 run) | 480 (24 prompts × 4 LLMs × 5 runs) |
| Haiku classification calls | 0 | ~192 (at ~40% mention rate across runs) |
| Monthly cost per client | ~$0.64 | ~$2.20 (with prompt caching) |
| Haiku classification cost | $0 | ~$0.04/month per client |

---

## 7. Phase Boundary

This phase does NOT include:
- Query management system (Phase 2)
- Competitive gap matrix with mention levels (Phase 3)
- Stability tracking (Phase 4)
- Mention × citation diagnosis or gap-closing workflow (Phase 5)

Queries remain as a flat `target_queries` array in client config until Phase 2. Competitor tracking remains binary until Phase 3.
