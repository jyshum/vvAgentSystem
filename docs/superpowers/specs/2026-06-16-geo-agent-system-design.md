# GEO Agent System — Validated Design Spec

**Date:** 2026-06-16
**Status:** Approved
**Source:** GEO_AGENT_SYSTEM.md (validated and corrected)

---

## 1. Overview

Victory Velocity's autonomous GEO agent system automates measurement, analysis, and recommendation for Generative Engine Optimization. The system queries 4 LLMs via API, audits client websites against 6 GEO pillars, pulls Search Console metrics, and generates actionable reports — replacing manual prompting and screenshotting.

## 2. Feasibility Validation Summary

### Confirmed Feasible

| Component | Status | Notes |
|---|---|---|
| LangGraph (Python) | Confirmed | StateGraph, conditional routing, `interrupt()` for HITL all verified |
| Google Search Console API | Confirmed | Returns impressions, clicks, CTR, position. Service account auth. 24-72h data delay. |
| Supabase (PostgreSQL) | Confirmed | Free tier (500MB) sufficient. Python + TS clients available. |
| Perplexity Sonar API | Confirmed | Built-in search. $1/$1 per MTok + $5/1K searches. |
| Anthropic Claude web search | Confirmed | `web_search` server tool. $10/1K searches + token costs. |
| Google Gemini Search grounding | Confirmed | 5,000 free searches/month, then $14/1K. |

### Corrections Required

| Spec Claim | Issue | Correction |
|---|---|---|
| GPT-4.1 Mini w/ web_search | GPT-4.1 Mini does not support web search | Use `gpt-4o-mini-search-preview` via Responses API |
| Reddit API free (100 req/min) | Free tier is non-commercial only. Agency use requires paid contract. | Defer Reddit scout. Apply for commercial access separately. |
| ~$2/month per client | Only counts token costs, not per-search fees | Actual cost ~$3.72/month including search fees ($10/1K Anthropic, $5/1K Perplexity, $14/1K Gemini after free tier) |
| GSC baseline data | Google disclosed impressions logging bug May 2025–April 2026 | Historical baselines may be inflated. Disclose to clients. |

### Deferred

| Component | Reason | Revisit When |
|---|---|---|
| Reddit Scout | Commercial API requires paid contract | After applying to Reddit for commercial access |
| ML models (XGBoost, etc.) | Insufficient training data at launch | Week 7-10 per original spec |
| Google AI Overviews / Bing Copilot / Grok | No clean APIs available | v3 per original spec |

## 3. Tracker Agent Design (Priority #1)

### Purpose

Query 4 LLMs with a client's target prompts using web search, parse responses for brand mentions and citations, calculate visibility scores, output results as JSON.

### Engine Configuration

| Engine | Model ID | Web Search Mechanism | Est. Cost/Query |
|---|---|---|---|
| ChatGPT | `gpt-4o-mini-search-preview` | `web_search` tool (Responses API) | ~$0.003 |
| Perplexity | `sonar` | Built-in search | ~$0.007 |
| Claude | `claude-haiku-4-5` | `web_search` server tool | ~$0.012 |
| Gemini | `gemini-2.5-flash` | Search grounding | ~$0.002 |

### Input

Client config JSON:

```json
{
  "client_name": "ChildSpot",
  "brand_name": "ChildSpot",
  "brand_variations": ["ChildSpot", "Child Spot", "childspot.ca"],
  "website_domain": "childspot.ca",
  "target_queries": [
    "best childcare finder in Ontario",
    "how to find daycare near me Ontario",
    "childcare waitlist Ontario"
  ],
  "competitors": ["OneList Ontario", "HiMama", "government waitlist"]
}
```

### Output per Query x Engine

```json
{
  "query": "best childcare finder in Ontario",
  "engine": "chatgpt",
  "model": "gpt-4o-mini-search-preview",
  "response_text": "...",
  "brand_mentioned": true,
  "brand_cited": false,
  "citation_url": null,
  "competitor_mentions": ["OneList Ontario"],
  "timestamp": "2026-06-17T10:30:00Z"
}
```

### Visibility Score

- Per engine: `(queries with brand mention or citation) / (total queries)`
- Aggregate: average across all engines
- Citation rate: `(queries with citation) / (total queries)` — weighted higher than mention-only

### Architecture

Standalone Python script for MVP. No LangGraph dependency yet — the tracker becomes a node in the LangGraph StateGraph in week 4.

Each engine is a pluggable async function. If an API key is missing or a call fails, that engine is skipped gracefully — the others still return results. Timeout: 30s per call, 3 retries with exponential backoff.

### Prompt Design

Each engine receives the target query as-is (e.g., "best childcare finder in Ontario"). No system prompt manipulation — the goal is to capture what a real user would see. Web search must be enabled so responses reflect current web knowledge.

### Brand Detection

Case-insensitive substring match against `brand_variations` list. Citation detection checks for URLs containing the client's domain. Competitor detection uses the same substring approach against the `competitors` list.

## 4. Corrected Build Order

| Phase | Build | Priority | Depends On |
|---|---|---|---|
| **Phase 1 (Day 1)** | Tracker agent — standalone, terminal/JSON output | CRITICAL — client call | API keys for 4 providers |
| **Phase 2 (Week 1)** | Supabase schema + client config system | High | Supabase project setup |
| **Phase 3 (Week 1-2)** | Tracker agent writes to Supabase | High | Phase 2 |
| **Phase 4 (Week 2)** | GSC agent + audit agent | High | Client GSC access granted |
| **Phase 5 (Week 3)** | Dashboard MVP (Next.js) — GEO metrics view | High | Phase 3 (data in Supabase) |
| **Phase 6 (Week 3)** | Competitor tracker (extracts from tracker results) | Medium | Phase 3 |
| **Phase 7 (Week 4)** | LangGraph graph + orchestrator + conditional routing | Medium | Phases 3-6 |
| **Phase 8 (Week 5)** | Schema agent + content recommender + HITL checkpoint | Medium | Phase 7 |
| **Phase 9 (Week 6)** | Report bridge (JSON export to vv-report-generator) | Medium | Phase 7 |
| **Phase 10 (TBD)** | Reddit scout | Low | Commercial API agreement |

## 5. Corrected Cost Estimates

### Per Client Per Month (at 80 queries/week = ~320/month)

| Item | Token Cost | Search Fee | Total |
|---|---|---|---|
| ChatGPT (80 queries) | ~$0.08 | ~$0.50 | ~$0.58 |
| Perplexity (80 queries) | ~$0.16 | ~$0.40 | ~$0.56 |
| Claude (80 queries) | ~$0.48 | ~$0.80 | ~$1.28 |
| Gemini (80 queries) | ~$0.05 | ~$0.00* | ~$0.05 |
| Audit agent | ~$0.84 | — | ~$0.84 |
| GSC agent | ~$0.00 | — | ~$0.00 |
| Orchestrator | ~$0.18 | — | ~$0.18 |
| Schema + content rec | ~$0.23 | — | ~$0.23 |
| **Total per client** | | | **~$3.72** |

*Gemini: free within 5,000 searches/month for 1-2 clients. At 3+ clients, add ~$1.12/client.

### Fixed Infrastructure

| Item | Cost/Month |
|---|---|
| Railway/Render VPS | $5-7 |
| Supabase free tier | $0 |
| Vercel free tier | $0 |
| **Total fixed** | **~$7** |

### Unit Economics

At 5 clients × $500/month = $2,500 revenue. Infrastructure: $7 + (5 × $3.72) = ~$25.60. **99.0% gross margin.** Still excellent.

## 6. Environment Variables Required

```
# LLM APIs
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
PERPLEXITY_API_KEY=
GOOGLE_GEMINI_API_KEY=

# Google Search Console (Phase 4)
GOOGLE_SERVICE_ACCOUNT_JSON=

# Database (Phase 2)
SUPABASE_URL=
SUPABASE_ANON_KEY=
```

## 7. Constraints

- Never use Opus models. Sonnet for reasoning/generation, Haiku for everything else.
- Enable prompt caching on every reusable system prompt.
- All LLM calls: 30s timeout, 3 retries, exponential backoff.
- Each agent independently testable with mock inputs.
- Errors logged, not thrown. Partial data > no data.
- Report bridge must match existing vv-report-generator format exactly.

## 8. Sources

- [LangGraph interrupt() docs](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [OpenAI GPT-4.1 Mini retirement notice](https://openai.com/index/retiring-gpt-4o-and-older-models/)
- [OpenAI web search API docs](https://developers.openai.com/api/docs/guides/tools-web-search)
- [Perplexity Sonar API pricing 2026](https://www.cloudzero.com/blog/perplexity-api-pricing/)
- [Anthropic web search API announcement](https://claude.com/blog/web-search-api)
- [Anthropic web search tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)
- [Google Gemini search grounding pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Reddit API pricing 2026](https://octolens.com/blog/reddit-api-pricing)
- [Reddit API commercial use restrictions](https://www.bbntimes.com/technology/complete-guide-to-reddit-api-pricing-and-usage-tiers-in-2026)
- [Google Search Console API guide](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data)
- [GSC impressions bug disclosure](https://www.seo-kreativ.de/en/blog/gsc-impressions-bug-google-logging-error/)
