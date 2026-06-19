# Victory Velocity — GEO Agent System
## Architectural Plan · MVP

> This document defines the architecture for Victory Velocity's autonomous GEO agent system. It is optimized for Claude Code implementation. It contains no hard code — only architectural direction, technology decisions, and credential requirements. Claude Code should use this as primary context and is encouraged to critique any decisions that conflict with feasibility.

---

## 1. Context

### What is Victory Velocity?

Victory Velocity (VV) is a GEO and ChatGPT Ads agency co-founded by Jared and Kaden. The agency helps businesses become visible in AI-generated responses across ChatGPT, Perplexity, Claude, and Gemini. VV's competitive advantage is a software-driven approach: an autonomous agent system that automates GEO measurement, analysis, and recommendation — replacing the manual process of prompting LLMs by hand and screenshotting results.

### What is GEO?

Generative Engine Optimization — making a brand appear when users ask AI a relevant question. Six pillars (per the Princeton KDD 2024 paper, arxiv.org/abs/2311.09735):

1. **Content Structure** — answer-first formatting, question headings, extractable sections (+40% citation lift)
2. **Fact Density** — statistics and data points every 150-200 words (+32% visibility)
3. **Source Citations** — citing authoritative external sources in your own content (+30-40%)
4. **Authority Signals** — third-party mentions on Reddit, review sites, forums, editorial press
5. **Schema Markup** — JSON-LD structured data: FAQPage, HowTo, LocalBusiness (+20-30%)
6. **Freshness** — content under 3 months old is 3x more likely to be cited

### What Already Exists

**Report Generator** — live at https://kadeny-128.github.io/vv-report-generator/ (repo: github.com/Kadeny-128/vv-report-generator). Static HTML/JS/CSS, no framework. Supports multi-client, multi-week tracking with:
- Search Console KPIs (impressions, clicks, CTR, avg position) with baselines and % change
- GEO spot checks across 7 engines (ChatGPT, Perplexity, Claude, Gemini, Google AI Overviews, Bing Copilot, Grok) with query × engine × cited × notes
- Executive summary, highlights, work completed, priorities, blockers, notes
- Multi-week trend sparklines and PDF export

Currently all data entry is manual. **The agent system's primary job is to automate the data that feeds this report.**

### What This System Replaces

| Currently Manual | Agent System Automates |
|---|---|
| Querying each LLM and screenshotting | Tracker agent queries 4 LLMs via API |
| Auditing site pages by hand | Audit agent crawls and scores every page |
| Searching Reddit for opportunities | Reddit scout surfaces top posts |
| Typing Search Console numbers | GSC agent pulls metrics via API |
| Writing reports from scratch | Report bridge exports data to report generator |

Content creation stays manual (Kaden writes). Reddit engagement stays manual (you post). The system finds, measures, analyzes, and recommends. Humans create and engage.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│              LangGraph Orchestration (Python)          │
│              Runs on VPS (Railway/Render)              │
│                                                        │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐     │
│  │Tracker │ │  GSC   │ │  Audit   │ │ Reddit   │     │
│  │ Agent  │ │ Agent  │ │  Agent   │ │  Scout   │     │
│  └───┬────┘ └───┬────┘ └────┬─────┘ └────┬─────┘     │
│      └─────┬────┴───────────┴─────────────┘           │
│            │                                           │
│     ┌──────▼───────┐                                   │
│     │ Orchestrator │ ← reasons about state, decides    │
│     └──────┬───────┘   which agents to activate        │
│            │                                           │
│     ┌──────▼───────┐  ┌──────────────┐                │
│     │   Schema     │  │   Content    │                │
│     │   Agent      │  │   Recomm.    │                │
│     └──────┬───────┘  └──────┬───────┘                │
│            └────────┬────────┘                         │
│                     │                                  │
│     ┌───────────────▼───────────────┐                  │
│     │   HUMAN CHECKPOINT            │                  │
│     │   LangGraph interrupt()       │                  │
│     │   Pauses until approval       │                  │
│     └───────────────┬───────────────┘                  │
│                     │                                  │
│     ┌───────────────▼───────────────┐                  │
│     │   Report Generation           │                  │
│     │   Formats data for export     │                  │
│     └───────────────────────────────┘                  │
│                                                        │
└────────────────────────┬───────────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │  Supabase   │
                  │ (all state) │
                  └──────┬──────┘
                         │
            ┌────────────┴────────────┐
            │                         │
     ┌──────▼──────┐          ┌───────▼───────┐
     │  Dashboard   │          │   Report Gen  │
     │  (Next.js)   │          │   (existing)  │
     │  internal    │          │  client-facing │
     └──────────────┘          └───────────────┘
```

### Why This Architecture

**Why LangGraph (not n8n, CrewAI, or plain scripts):**
LangGraph is the production standard for multi-agent systems in 2026 (27,100 monthly searches, most GitHub examples, best documentation). It provides three things critical to this system that alternatives don't handle well together: (1) typed state that flows through every agent, (2) conditional routing where the orchestrator decides at runtime which agents to call, and (3) native human-in-the-loop via `interrupt()` that pauses the graph until approval. n8n is faster to prototype but weak at complex state management and has no native ML integration path. CrewAI abstracts away too much orchestration detail. Plain Python scripts would require reinventing state management and checkpointing. Reference implementations: github.com/langchain-ai/langgraph-swarm-py, github.com/expectbugs/agents.

**Why Python for agents, TypeScript for dashboard:**
LangGraph's Python SDK is significantly more mature than TypeScript. When ML models are added in v2 (XGBoost, scikit-learn, PyTorch), they import natively in Python. The dashboard is Next.js (team expertise). They communicate exclusively through Supabase — no shared runtime, no imports between them.

**Why API tracking (not headless browsers):**
Headless browser scraping (Playwright) is fragile — bot detection, CAPTCHAs, ToS violations, constant maintenance. API calls with web search enabled are reliable, cheap, and the industry standard approach used by ZipTie, Otterly, and Profound. The gap between API-with-web-search and real chat UI exists but is acceptable and documented for client transparency. For teams that need exact UI replication, services like Cloro.dev and Bright Data's LLM Scrapers exist as paid alternatives — these can be evaluated as a v2 upgrade if API accuracy proves insufficient.

**Why semi-autonomous (not fully autonomous):**
All outputs go to an approval queue. Nothing touches a client's website without human review. Trust is earned over cycles. Confidence-based auto-execution is a v2 feature unlocked after the system proves reliable.

---

## 3. Tech Stack

| Layer | Technology | Cost |
|---|---|---|
| Agent orchestration | LangGraph (Python) | Free (open source) |
| Orchestrator / content LLM | Claude Sonnet 4.6 (Anthropic API) | ~$3/MTok in, $15/MTok out |
| Audit / parsing / schema LLM | Claude Haiku 4.5 (Anthropic API) | ~$1/MTok in, $5/MTok out |
| Tracker — ChatGPT | OpenAI API, GPT-4.1 Mini w/ web_search | $0.40/MTok in, $1.60/MTok out |
| Tracker — Perplexity | Sonar API (search built in) | $1/MTok in, $1/MTok out |
| Tracker — Claude | Anthropic API, Haiku w/ web search | $1/MTok in, $5/MTok out |
| Tracker — Gemini | Google Gemini API w/ Search grounding | ~$0.15/MTok in, $0.60/MTok out |
| GSC metrics | Google Search Console API | Free |
| Reddit search | Reddit REST API (OAuth2) | Free (100 req/min) |
| Database | Supabase (PostgreSQL) | Free tier (500MB) |
| Dashboard | Next.js + Tailwind on Vercel | Free tier |
| Agent hosting | Railway or Render VPS | $5-7 USD/month |

### Monthly Cost Per Client

| Agent | Cost/month |
|---|---|
| Tracker (80 API calls/week) | ~$0.64 |
| Audit (20 pages/week) | ~$0.84 |
| GSC agent | ~$0.00 (free API) |
| Orchestrator | ~$0.18 |
| Schema + content rec | ~$0.23 |
| Reddit scout | ~$0.10 |
| **Total per client** | **~$2.00** |

**Fixed infrastructure: ~$7/month** regardless of client count.
**With prompt caching + batch API: costs reduce 50-70%.**

At 5 clients charging $500/month each: $2,500 revenue, ~$17 infrastructure cost. 99.3% gross margin.

---

## 4. Credentials Needed

**This is what to ask clients for and what to set up internally.**

### From Each Client

| Credential | What It Is | How Client Provides It | Why You Need It |
|---|---|---|---|
| Google Search Console access | Viewer permission on their GSC property | They add your Google account email in GSC → Settings → Users → Add user → Restricted | Automated impressions, clicks, CTR, position data |
| Website URL | Their site URL | They tell you | Audit agent crawls it |
| Target queries | What prompts they want to rank for | Discuss on onboarding call | Tracker agent queries these |
| Competitor names | Who they consider competition | Discuss on onboarding call | Competitor tracking |
| Brand name variations | All ways their brand might be mentioned | Discuss on onboarding call | Mention detection in LLM responses |

**For tomorrow's ChildSpot call, ask for:**
1. "Can you add us as a viewer in your Google Search Console?" — this is the most important credential
2. "Is your site custom-built or on a CMS like WordPress?" — determines future deploy integration
3. "Who are your main competitors?" — OneList Ontario, government waitlist systems, etc.
4. "What questions do parents ask when looking for childcare?" — these become target queries

### Internal Setup (One-Time)

| Credential | Where to Get It | What It Costs |
|---|---|---|
| Anthropic API key | console.anthropic.com | Pay-per-use (~$5 free credits to start) |
| OpenAI API key | platform.openai.com | Pay-per-use |
| Perplexity API key | docs.perplexity.ai | Pay-per-use |
| Google Gemini API key | aistudio.google.com | Free tier available |
| Google Service Account (for GSC) | Google Cloud Console → IAM → Service Accounts | Free |
| Reddit OAuth app | reddit.com/prefs/apps → create "script" type app | Free |
| Supabase project | supabase.com | Free tier |
| Railway/Render account | railway.app or render.com | $5-7/month |

---

## 5. Agent Flow — What Each Agent Does

### Cycle Flow (Runs Weekly Per Client)

```
START
  │
  ├── Tracker Agent ──────── queries 4 LLMs with target prompts
  │                          parses for brand mentions + citations
  │                          calculates visibility score + delta
  │
  ├── GSC Agent ─────────── pulls Search Console metrics via API
  │   (parallel)             impressions, clicks, CTR, position
  │                          calculates week-over-week change
  │
  ├── Audit Agent ────────── crawls client site (any platform)
  │                          scores each page on 6 GEO pillars
  │                          identifies weakest pages + pillars
  │
  ├── Competitor Tracker ─── extracts competitor mentions from
  │                          tracker results (no extra API calls)
  │                          detects new/rising competitors
  │
  └── Reddit Scout ──────── searches Reddit REST API for posts
                             matching client's intent signals
                             scores by freshness + relevance
                             surfaces top 5-10 opportunities
  │
  ▼
ORCHESTRATOR
  │  Receives full state from all agents above
  │  Loads previous 3 cycles for trend analysis
  │  Calls Claude Sonnet to reason about priorities
  │  Outputs a plan: which actions to take and why
  │  May decide to skip action entirely if scores are improving
  │
  ├── Schema Agent ──────── generates JSON-LD for flagged pages
  │   (if orchestrator       validates against schema requirements
  │    decides)
  │
  ├── Content Recommender── generates specific improvement recs
  │   (if orchestrator       for weak pages or uncovered queries
  │    decides)              optional draft content
  │
  └── Skip ──────────────── if no action needed, wait
  │
  ▼
HUMAN CHECKPOINT (LangGraph interrupt)
  │  Graph pauses
  │  Dashboard displays: schema outputs, content recs,
  │    Reddit opportunities, orchestrator reasoning
  │  Human approves/rejects/engages
  │  Graph resumes when approvals are written to Supabase
  │
  ▼
REPORT GENERATION
  │  Takes finalized state
  │  Calls Claude Haiku to generate narrative sections:
  │    Executive summary, highlights, work completed,
  │    priorities, blockers
  │  Formats all data for report generator import
  │
  ▼
END → schedule next cycle
```

### What Makes This an Agent (Not a Pipeline)

A pipeline runs every step in the same order every time. This system makes runtime decisions:

- The orchestrator may call the schema agent but not the content recommender (or vice versa, or neither)
- The orchestrator may shift strategy mid-project: "content fixes aren't moving scores → switch focus to authority"
- The orchestrator may decide to do nothing and just monitor if scores are improving
- Different observations produce different plans — the reasoning is generated by an LLM at runtime

### The 7 vs 4 Engine Gap

The report generator tracks 7 engines. The agent automates 4 (ChatGPT, Perplexity, Claude, Gemini). Three engines lack clean APIs:

| Engine | Why Not Automated | MVP Approach |
|---|---|---|
| Google AI Overviews | Embedded in Google Search, no API | Manual check, enter in report generator |
| Bing Copilot | No public API | Manual check, enter in report generator |
| Grok | xAI API maturity unclear | Manual check, enter in report generator |

The report bridge exports the 4 automated results. The 3 manual ones continue to be entered by hand. This is the same hybrid approach used by most GEO tools in 2026 — full automation across all engines doesn't exist yet at any price point.

---

## 6. Report Generator Integration

The agent system's data must map exactly to the report generator's fields. The report bridge is a JSON export that the report generator can import, replacing manual data entry.

### Field Mapping

| Report Generator Field | Data Source | Automated? |
|---|---|---|
| Week starting | Cycle start date | Yes |
| Client domain | Client config | Yes |
| Total Impressions (current + baseline) | GSC agent | Yes |
| Total Clicks (current + baseline) | GSC agent | Yes |
| Avg CTR % (current + baseline) | GSC agent | Yes |
| Avg Position (current + baseline) | GSC agent | Yes |
| GEO Spot Checks (query × engine × cited × notes) | Tracker agent | Yes (4 engines) |
| Executive Summary | Report generation step (Claude) | Yes |
| Highlights / Wins | Derived from visibility deltas + new citations | Yes |
| Work Completed | Approved schema + content recommendations | Yes |
| Next Week Priorities | Orchestrator's plan for next cycle | Yes |
| Blockers / Risks | Error logs + stalled scores | Yes |
| Notes | Generated from orchestrator reasoning | Yes |

The export format must match the internal data model used in `app.js` of the vv-report-generator repo. The report bridge reads the cycle state from Supabase, transforms it into the report generator's expected JSON structure, and outputs a downloadable file that can be imported into the report builder.

---

## 7. Repo Structure

```
geo-platform/
├── GEO_AGENT_SYSTEM.md           ← this document
│
├── agents/                        ← Python (LangGraph)
│   ├── pyproject.toml
│   ├── src/
│   │   ├── graph.py               ← LangGraph StateGraph definition
│   │   ├── state.py               ← state type definitions (Pydantic)
│   │   ├── agents/
│   │   │   ├── tracker.py
│   │   │   ├── gsc.py
│   │   │   ├── auditor.py
│   │   │   ├── competitor.py
│   │   │   ├── reddit_scout.py
│   │   │   ├── orchestrator.py
│   │   │   ├── schema_gen.py
│   │   │   ├── content_rec.py
│   │   │   └── report_gen.py
│   │   ├── llm/                   ← LLM client wrappers
│   │   └── config/                ← client config loader
│   └── run.py                     ← entry point
│
├── dashboard/                     ← TypeScript (Next.js)
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx           ← cycle overview
│       │   ├── approvals/         ← approval queue
│       │   ├── audit/             ← site audit results
│       │   └── history/           ← past cycles
│       └── lib/
│           └── supabase.ts
│
├── clients/                       ← JSON config files
│   ├── childspot.json
│   └── _template.json
│
├── database/
│   └── schema.sql
│
└── .env                           ← API keys (gitignored)
```

Agents and dashboard are fully separate. They share nothing except the Supabase database. Agents run on VPS. Dashboard deploys to Vercel.

---

## 8. Key Decisions

| Decision | Choice | Why |
|---|---|---|
| Orchestration framework | LangGraph (Python) | Most mature agent framework. Native state management, conditional routing, human-in-the-loop. Direct ML integration path for v2. Industry standard with most production examples. |
| Agent language | Python | LangGraph Python SDK is more mature than TS. ML libraries (scikit-learn, XGBoost, PyTorch) import natively. Reddit and Google API ecosystems are Python-first. |
| Dashboard language | TypeScript / Next.js | Team expertise. Vercel deployment. No shared runtime with agents — communicates via Supabase only. |
| LLM tracking method | API calls with web search enabled | Reliable, cheap, no bot detection. Industry standard (ZipTie, Otterly, Profound all use similar approaches). Headless browser scraping is fragile and violates ToS. Bright Data LLM Scrapers or Cloro.dev are paid alternatives for v2 if API accuracy is insufficient. |
| GSC data | Google Search Console API with service account | Free, fully automated, returns exact metrics the report generator needs. 2-day data delay is irrelevant for weekly cycles. |
| Reddit approach | REST API direct (not PRAW) | PRAW failed previously due to credential issues. Reddit's REST API works via standard HTTP with OAuth2. No Python library dependency required. TypeScript-equivalent also possible via fetch. |
| Database | Supabase (PostgreSQL) | Free tier sufficient. Great Python and TypeScript clients. Realtime subscriptions available for checkpoint resume. Managed service — no ops. |
| Autonomy level | Semi-autonomous (approval queue) | All outputs require human approval in MVP. Auto-execution gated behind confidence thresholds added in v2 after system proves reliable over multiple cycles. |
| ML in MVP | None — collected passively | Insufficient training data on day one. Tracker and audit agents passively collect training data every cycle. Models trained and integrated in v2 (~week 7-10). Supplemented by GEO-Bench dataset (huggingface.co/datasets/GEO-Optim/geo-bench, 10K queries). |
| Report integration | JSON export bridge to existing report generator | Report generator already works. Don't rebuild — feed data into it. Bridge transforms Supabase state into the report generator's expected JSON format. |

---

## 9. Post-MVP Roadmap

| Version | Feature | Depends On |
|---|---|---|
| v2 | Citability Scorer (XGBoost) — predicts whether a page will be cited | 6 weeks of tracker + audit data |
| v2 | Prediction Model — estimates impact of each fix on visibility | 8 weeks of tracker data |
| v2 | Confidence-based auto-execution — high-confidence actions skip approval | Proven system reliability |
| v2 | CMS integration — push drafts to WordPress/Webflow via API | Knowing client CMS stacks |
| v2 | Bright Data or Cloro.dev integration — exact UI replication for tracking | Budget for paid scraping APIs |
| v3 | Google AI Overviews / Bing Copilot / Grok tracking | Scraping infrastructure or API availability |
| v3 | Client-facing dashboard with auth | Client count justifying the build |
| v3 | Sentiment classifier (distilBERT) on brand mentions | 300+ labeled mention examples |

---

## 10. Build Order

| Week | Build | Test With |
|---|---|---|
| 1 | Supabase schema + client config system + tracker agent | ChildSpot target queries |
| 2 | GSC agent + audit agent | ChildSpot site + Search Console |
| 3 | Reddit scout + competitor tracker | ChildSpot intent signals |
| 4 | LangGraph graph + orchestrator + conditional routing | Full cycle on ChildSpot |
| 5 | Schema agent + content recommender + human checkpoint | Orchestrator-driven actions |
| 6 | Dashboard MVP + report bridge + JSON export | Import into report generator |

---

## 11. Environment Variables

```
# LLM APIs
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
PERPLEXITY_API_KEY=
GOOGLE_GEMINI_API_KEY=

# Google Search Console
GOOGLE_SERVICE_ACCOUNT_JSON=    # path to service account key file

# Reddit
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=

# Notifications (optional)
SLACK_WEBHOOK_URL=
```

---

## 12. Constraints for Implementation

- **Never use Opus models.** Sonnet for reasoning and generation. Haiku for everything else.
- **Enable prompt caching** on every API call that reuses a system prompt. Single biggest cost lever.
- **All LLM calls must have timeout and retry logic** (3 retries, exponential backoff). One API failure should never crash a cycle.
- **The report bridge must match the exact data format of the existing report generator** (vv-report-generator/app.js). Do not modify the report generator — adapt the export to fit it.
- **Each agent must be independently testable** with mock state inputs and verified outputs.
- **Errors are logged, not thrown.** If one agent fails, the cycle continues with partial data. The orchestrator receives incomplete state and notes the gap in its reasoning.
