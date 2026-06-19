# GEO Tracker Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone tracker agent that queries 4 LLMs (ChatGPT, Perplexity, Claude, Gemini) with a client's target prompts, detects brand mentions and citations, computes visibility scores, and outputs results as CSV + JSON for fact-checking.

**Architecture:** Single Python package with one module per LLM engine. A tracker orchestrator calls each engine sequentially, runs brand/competitor detection on the response text, computes per-engine and aggregate visibility scores, and writes results to CSV (for spreadsheet review) and JSON (for programmatic use). Each engine is independent — if one fails or lacks an API key, it's skipped gracefully.

**Tech Stack:** Python 3.11+, `openai` SDK (ChatGPT + Perplexity), `anthropic` SDK (Claude), `google-genai` SDK (Gemini), `python-dotenv`, `pytest`

---

## File Structure

```
vvAgentSystem/
├── agents/
│   ├── pyproject.toml              ← package definition + dependencies
│   ├── .env.example                ← template for API keys
│   ├── run.py                      ← CLI entry point
│   ├── src/
│   │   ├── __init__.py
│   │   ├── detection.py            ← brand mention + citation + competitor detection
│   │   ├── output.py               ← CSV + JSON + terminal formatting
│   │   ├── tracker.py              ← orchestrator: runs engines, computes scores
│   │   └── engines/
│   │       ├── __init__.py         ← engine registry, skip-on-missing-key logic
│   │       ├── chatgpt.py          ← OpenAI gpt-4o-mini + web_search (Responses API)
│   │       ├── perplexity.py       ← Perplexity Sonar via OpenAI-compatible endpoint
│   │       ├── claude.py           ← Anthropic Claude Haiku + web_search server tool
│   │       └── gemini.py           ← Google Gemini 2.5 Flash + Search grounding
│   └── tests/
│       ├── test_detection.py       ← unit tests for brand/competitor detection
│       └── test_output.py          ← unit tests for CSV/JSON formatting
├── clients/
│   └── childspot.json              ← ChildSpot client config
└── output/                         ← generated CSV + JSON files (gitignored)
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `agents/pyproject.toml`
- Create: `agents/.env.example`
- Create: `agents/src/__init__.py`
- Create: `agents/src/engines/__init__.py`
- Create: `agents/tests/__init__.py` (empty, needed for pytest discovery)
- Create: `clients/childspot.json`
- Create: `.gitignore`

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem
mkdir -p agents/src/engines agents/tests clients output
```

- [ ] **Step 2: Write pyproject.toml**

Create `agents/pyproject.toml`:

```toml
[project]
name = "geo-tracker"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.82.0",
    "anthropic>=0.52.0",
    "google-genai>=1.14.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]
```

- [ ] **Step 3: Write .env.example**

Create `agents/.env.example`:

```
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_GEMINI_API_KEY=AIza...
```

- [ ] **Step 4: Write client config**

Create `clients/childspot.json`:

```json
{
  "client_name": "ChildSpot",
  "brand_name": "ChildSpot",
  "brand_variations": ["ChildSpot", "Child Spot", "childspot.ca"],
  "website_domain": "childspot.ca",
  "target_queries": [
    "best childcare finder in Ontario",
    "how to find daycare near me Ontario",
    "childcare waitlist Ontario",
    "Ontario childcare registry",
    "find licensed daycare Ontario"
  ],
  "competitors": ["OneList Ontario", "HiMama"]
}
```

- [ ] **Step 5: Write .gitignore**

Create `.gitignore`:

```
.env
output/
__pycache__/
*.egg-info/
.venv/
```

- [ ] **Step 6: Create empty __init__.py files**

Create `agents/src/__init__.py` (empty file).
Create `agents/src/engines/__init__.py` (empty file — will be populated in Task 7).
Create `agents/tests/__init__.py` (empty file).

- [ ] **Step 7: Install dependencies**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: all packages install successfully.

- [ ] **Step 8: Set up .env with real API keys**

Copy `.env.example` to `.env` and fill in real API keys. You need to create accounts and get keys from:
- https://platform.openai.com/api-keys (OpenAI)
- https://www.perplexity.ai/settings/api (Perplexity)
- https://console.anthropic.com/settings/keys (Anthropic)
- https://aistudio.google.com/apikey (Google Gemini)

Each provider requires a billing method on file. Anthropic may have free credits for new accounts. Google Gemini has a free tier.

- [ ] **Step 9: Commit**

```bash
git init
git add agents/pyproject.toml agents/.env.example agents/src/__init__.py agents/src/engines/__init__.py agents/tests/__init__.py clients/childspot.json .gitignore
git commit -m "feat: project scaffolding for GEO tracker agent"
```

---

## Task 2: Brand and Competitor Detection (TDD)

**Files:**
- Create: `agents/tests/test_detection.py`
- Create: `agents/src/detection.py`

- [ ] **Step 1: Write failing tests**

Create `agents/tests/test_detection.py`:

```python
from src.detection import detect_brand, detect_competitors


class TestDetectBrand:
    def test_brand_mentioned_exact_match(self):
        text = "ChildSpot is a popular childcare platform in Ontario."
        result = detect_brand(text, ["ChildSpot", "Child Spot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is False
        assert result["citation_url"] is None

    def test_brand_mentioned_case_insensitive(self):
        text = "You might want to check out childspot for daycare listings."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True

    def test_brand_mentioned_variation(self):
        text = "Child Spot is a helpful resource for parents."
        result = detect_brand(text, ["ChildSpot", "Child Spot"], "childspot.ca")
        assert result["brand_mentioned"] is True

    def test_brand_not_mentioned(self):
        text = "There are several government resources for finding daycare."
        result = detect_brand(text, ["ChildSpot", "Child Spot"], "childspot.ca")
        assert result["brand_mentioned"] is False
        assert result["brand_cited"] is False

    def test_brand_cited_with_url(self):
        text = "You can find daycare at https://childspot.ca/search which lists providers."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is True
        assert result["citation_url"] == "https://childspot.ca/search"

    def test_brand_cited_with_url_in_markdown(self):
        text = "Check [ChildSpot](https://www.childspot.ca) for listings."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is True
        assert "childspot.ca" in result["citation_url"]

    def test_domain_mention_counts_as_citation(self):
        text = "Visit childspot.ca for Ontario daycare options."
        result = detect_brand(text, ["ChildSpot"], "childspot.ca")
        assert result["brand_mentioned"] is True
        assert result["brand_cited"] is True


class TestDetectCompetitors:
    def test_single_competitor_found(self):
        text = "OneList Ontario is the government's official waitlist system."
        result = detect_competitors(text, ["OneList Ontario", "HiMama"])
        assert result == ["OneList Ontario"]

    def test_multiple_competitors_found(self):
        text = "Alternatives include OneList Ontario and HiMama for tracking."
        result = detect_competitors(text, ["OneList Ontario", "HiMama"])
        assert "OneList Ontario" in result
        assert "HiMama" in result

    def test_no_competitors_found(self):
        text = "There are various childcare platforms available."
        result = detect_competitors(text, ["OneList Ontario", "HiMama"])
        assert result == []

    def test_competitor_case_insensitive(self):
        text = "himama is a popular daycare management app."
        result = detect_competitors(text, ["HiMama"])
        assert result == ["HiMama"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/test_detection.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.detection'`

- [ ] **Step 3: Implement detection.py**

Create `agents/src/detection.py`:

```python
import re


def detect_brand(
    response_text: str,
    brand_variations: list[str],
    website_domain: str,
) -> dict:
    text_lower = response_text.lower()
    domain_lower = website_domain.lower()

    brand_mentioned = any(v.lower() in text_lower for v in brand_variations)

    citation_url = None
    brand_cited = False

    if domain_lower in text_lower:
        brand_cited = True
        brand_mentioned = True
        urls = re.findall(r"https?://[^\s\)\]\"'>]+", response_text)
        for url in urls:
            if domain_lower in url.lower():
                citation_url = url
                break
        if citation_url is None:
            citation_url = f"https://{website_domain}"

    return {
        "brand_mentioned": brand_mentioned,
        "brand_cited": brand_cited,
        "citation_url": citation_url,
    }


def detect_competitors(
    response_text: str,
    competitors: list[str],
) -> list[str]:
    text_lower = response_text.lower()
    return [c for c in competitors if c.lower() in text_lower]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/test_detection.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/detection.py agents/tests/test_detection.py
git commit -m "feat: brand and competitor detection with tests"
```

---

## Task 3: Output Formatting (TDD)

**Files:**
- Create: `agents/tests/test_output.py`
- Create: `agents/src/output.py`

- [ ] **Step 1: Write failing tests**

Create `agents/tests/test_output.py`:

```python
import csv
import json
from pathlib import Path

from src.output import write_csv, write_json, format_summary


SAMPLE_RESULTS = [
    {
        "query": "best childcare finder in Ontario",
        "engine": "chatgpt",
        "model": "gpt-4o-mini",
        "response_text": "ChildSpot is a great platform for finding childcare.",
        "brand_mentioned": True,
        "brand_cited": False,
        "citation_url": None,
        "competitor_mentions": ["OneList Ontario"],
        "timestamp": "2026-06-17T10:00:00",
    },
    {
        "query": "best childcare finder in Ontario",
        "engine": "perplexity",
        "model": "sonar",
        "response_text": "Government resources are your best bet for childcare.",
        "brand_mentioned": False,
        "brand_cited": False,
        "citation_url": None,
        "competitor_mentions": [],
        "timestamp": "2026-06-17T10:00:01",
    },
]

SAMPLE_SCORES = {
    "per_engine": {
        "chatgpt": {"mention_rate": 1.0, "citation_rate": 0.0},
        "perplexity": {"mention_rate": 0.0, "citation_rate": 0.0},
    },
    "aggregate_mention_rate": 0.5,
    "aggregate_citation_rate": 0.0,
}


class TestWriteCsv:
    def test_creates_csv_with_correct_headers(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            assert "query" in reader.fieldnames
            assert "engine" in reader.fieldnames
            assert "response_text" in reader.fieldnames
            assert "brand_mentioned" in reader.fieldnames

    def test_csv_has_correct_row_count(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_csv_preserves_full_response_text(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["response_text"] == "ChildSpot is a great platform for finding childcare."

    def test_csv_competitor_mentions_joined(self, tmp_path):
        path = tmp_path / "test.csv"
        write_csv(SAMPLE_RESULTS, path)
        with open(path) as f:
            reader = csv.DictReader(f)
            row = next(reader)
        assert row["competitor_mentions"] == "OneList Ontario"


class TestWriteJson:
    def test_creates_valid_json(self, tmp_path):
        path = tmp_path / "test.json"
        write_json(SAMPLE_RESULTS, SAMPLE_SCORES, "ChildSpot", path)
        data = json.loads(path.read_text())
        assert "results" in data
        assert "visibility_scores" in data
        assert "client_name" in data

    def test_json_contains_all_results(self, tmp_path):
        path = tmp_path / "test.json"
        write_json(SAMPLE_RESULTS, SAMPLE_SCORES, "ChildSpot", path)
        data = json.loads(path.read_text())
        assert len(data["results"]) == 2

    def test_json_contains_scores(self, tmp_path):
        path = tmp_path / "test.json"
        write_json(SAMPLE_RESULTS, SAMPLE_SCORES, "ChildSpot", path)
        data = json.loads(path.read_text())
        assert data["visibility_scores"]["aggregate_mention_rate"] == 0.5


class TestFormatSummary:
    def test_summary_contains_engine_scores(self):
        text = format_summary(SAMPLE_SCORES, "ChildSpot")
        assert "chatgpt" in text.lower()
        assert "perplexity" in text.lower()

    def test_summary_contains_aggregate(self):
        text = format_summary(SAMPLE_SCORES, "ChildSpot")
        assert "50" in text or "0.5" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/test_output.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.output'`

- [ ] **Step 3: Implement output.py**

Create `agents/src/output.py`:

```python
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


CSV_FIELDS = [
    "query",
    "engine",
    "model",
    "brand_mentioned",
    "brand_cited",
    "citation_url",
    "competitor_mentions",
    "response_text",
    "timestamp",
]


def write_csv(results: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, "") for k in CSV_FIELDS}
            if isinstance(row["competitor_mentions"], list):
                row["competitor_mentions"] = "; ".join(row["competitor_mentions"])
            writer.writerow(row)


def write_json(
    results: list[dict],
    scores: dict,
    client_name: str,
    output_path: Path,
) -> None:
    report = {
        "client_name": client_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "visibility_scores": scores,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def format_summary(scores: dict, client_name: str) -> str:
    lines = [
        f"\n{'='*50}",
        f"  GEO Visibility Report: {client_name}",
        f"{'='*50}",
    ]
    for engine, engine_scores in scores["per_engine"].items():
        mention = engine_scores["mention_rate"]
        citation = engine_scores["citation_rate"]
        lines.append(f"  {engine:<15} mention: {mention:>6.0%}   cited: {citation:>6.0%}")
    lines.append(f"{'─'*50}")
    agg_mention = scores["aggregate_mention_rate"]
    agg_citation = scores["aggregate_citation_rate"]
    lines.append(f"  {'AGGREGATE':<15} mention: {agg_mention:>6.0%}   cited: {agg_citation:>6.0%}")
    lines.append(f"{'='*50}\n")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
python -m pytest tests/test_output.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/src/output.py agents/tests/test_output.py
git commit -m "feat: CSV + JSON + terminal output formatting with tests"
```

---

## Task 4: Retry Utility

**Files:**
- Create: `agents/src/retry.py`

Every engine call needs timeout and retry logic per the system constraints: 30s timeout, 3 retries, exponential backoff.

- [ ] **Step 1: Implement retry.py**

Create `agents/src/retry.py`:

```python
import time
import functools


def with_retries(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"    retry {attempt + 1}/{max_retries} in {delay:.0f}s — {e}")
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator
```

- [ ] **Step 2: Commit**

```bash
git add agents/src/retry.py
git commit -m "feat: retry utility with exponential backoff"
```

---

## Task 5: ChatGPT Engine

**Files:**
- Create: `agents/src/engines/chatgpt.py`

**API reference:** https://developers.openai.com/api/docs/guides/tools-web-search

- [ ] **Step 1: Implement chatgpt.py**

Create `agents/src/engines/chatgpt.py`:

```python
import os

from openai import OpenAI

from src.retry import with_retries


MODEL = "gpt-4o-mini"


@with_retries()
def query(prompt: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=30.0)
    response = client.responses.create(
        model=MODEL,
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    return response.output_text
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.engines.chatgpt import query
print(query('best childcare finder in Ontario'))
"
```

Expected: a text response mentioning childcare resources in Ontario. If you get an auth error, check your `OPENAI_API_KEY` in `.env`. If you get a model error, try `gpt-4o-mini-search-preview` instead of `gpt-4o-mini` as the MODEL value.

- [ ] **Step 3: Commit**

```bash
git add agents/src/engines/chatgpt.py
git commit -m "feat: ChatGPT engine with web search"
```

---

## Task 6: Perplexity Engine

**Files:**
- Create: `agents/src/engines/perplexity.py`

**API reference:** https://docs.perplexity.ai/api-reference/chat-completions

Perplexity's API is OpenAI-compatible. Search is built in — every Sonar query searches the web automatically.

- [ ] **Step 1: Implement perplexity.py**

Create `agents/src/engines/perplexity.py`:

```python
import os

from openai import OpenAI

from src.retry import with_retries


MODEL = "sonar"


@with_retries()
def query(prompt: str) -> str:
    client = OpenAI(
        api_key=os.environ["PERPLEXITY_API_KEY"],
        base_url="https://api.perplexity.ai",
        timeout=30.0,
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.engines.perplexity import query
print(query('best childcare finder in Ontario'))
"
```

Expected: a text response with citations (Perplexity typically includes `[1]`, `[2]` style references).

- [ ] **Step 3: Commit**

```bash
git add agents/src/engines/perplexity.py
git commit -m "feat: Perplexity Sonar engine"
```

---

## Task 7: Claude Engine

**Files:**
- Create: `agents/src/engines/claude.py`

**API reference:** https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool

The web search tool is a server-side tool — Anthropic executes the searches. The response contains multiple content blocks; extract the `text` blocks.

- [ ] **Step 1: Implement claude.py**

Create `agents/src/engines/claude.py`:

```python
import os

import anthropic

from src.retry import with_retries


MODEL = "claude-haiku-4-5"


@with_retries()
def query(prompt: str) -> str:
    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        timeout=30.0,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
    return "\n".join(text_parts)
```

> **Note on tool type version:** The tool type string (e.g. `web_search_20250305`) is versioned by Anthropic. If you get an error about an invalid tool type, check the current version at the API docs link above and update the string.

- [ ] **Step 2: Smoke test**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.engines.claude import query
print(query('best childcare finder in Ontario'))
"
```

Expected: a text response. May include citation references inline.

- [ ] **Step 3: Commit**

```bash
git add agents/src/engines/claude.py
git commit -m "feat: Claude engine with web search"
```

---

## Task 8: Gemini Engine

**Files:**
- Create: `agents/src/engines/gemini.py`

**API reference:** https://ai.google.dev/gemini-api/docs/google-search

Uses the `google-genai` SDK (the modern SDK, not the legacy `google-generativeai`).

- [ ] **Step 1: Implement gemini.py**

Create `agents/src/engines/gemini.py`:

```python
import os

from google import genai
from google.genai import types

from src.retry import with_retries


MODEL = "gemini-2.5-flash"


@with_retries()
def query(prompt: str) -> str:
    client = genai.Client(api_key=os.environ["GOOGLE_GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return response.text
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.engines.gemini import query
print(query('best childcare finder in Ontario'))
"
```

Expected: a text response grounded in Google Search results.

- [ ] **Step 3: Commit**

```bash
git add agents/src/engines/gemini.py
git commit -m "feat: Gemini engine with search grounding"
```

---

## Task 9: Engine Registry

**Files:**
- Modify: `agents/src/engines/__init__.py`

The registry loads available engines based on which API keys are present in the environment. Missing keys = engine skipped (with a warning), not a crash.

- [ ] **Step 1: Implement engine registry**

Write `agents/src/engines/__init__.py`:

```python
import os
import sys

ENGINES = {}


def _try_register(name: str, module_path: str, env_var: str, model: str) -> None:
    if not os.environ.get(env_var):
        print(f"  [SKIP] {name}: {env_var} not set", file=sys.stderr)
        return
    try:
        import importlib
        mod = importlib.import_module(module_path)
        ENGINES[name] = {"query": mod.query, "model": model}
    except Exception as e:
        print(f"  [SKIP] {name}: failed to load — {e}", file=sys.stderr)


def load_engines() -> dict:
    ENGINES.clear()
    _try_register("chatgpt", "src.engines.chatgpt", "OPENAI_API_KEY", "gpt-4o-mini")
    _try_register("perplexity", "src.engines.perplexity", "PERPLEXITY_API_KEY", "sonar")
    _try_register("claude", "src.engines.claude", "ANTHROPIC_API_KEY", "claude-haiku-4-5")
    _try_register("gemini", "src.engines.gemini", "GOOGLE_GEMINI_API_KEY", "gemini-2.5-flash")
    return ENGINES
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.engines import load_engines
engines = load_engines()
print(f'Loaded engines: {list(engines.keys())}')
"
```

Expected: lists whichever engines have API keys set. Prints `[SKIP]` messages for missing keys.

- [ ] **Step 3: Commit**

```bash
git add agents/src/engines/__init__.py
git commit -m "feat: engine registry with graceful skip on missing keys"
```

---

## Task 10: Tracker Orchestrator

**Files:**
- Create: `agents/src/tracker.py`

The tracker loads the client config, runs each available engine against each target query, performs detection, computes visibility scores, and returns structured results.

- [ ] **Step 1: Implement tracker.py**

Create `agents/src/tracker.py`:

```python
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.detection import detect_brand, detect_competitors
from src.engines import load_engines


def load_client_config(config_path: str) -> dict:
    return json.loads(Path(config_path).read_text())


def run_tracker(config: dict) -> tuple[list[dict], dict]:
    engines = load_engines()
    if not engines:
        raise RuntimeError("No engines available. Check your API keys in .env")

    results = []
    queries = config["target_queries"]
    brand_variations = config["brand_variations"]
    website_domain = config["website_domain"]
    competitors = config.get("competitors", [])

    total = len(queries) * len(engines)
    count = 0

    for query_text in queries:
        for engine_name, engine_info in engines.items():
            count += 1
            print(f"  [{count}/{total}] {engine_name}: {query_text[:50]}...")

            try:
                response_text = engine_info["query"](query_text)
                brand = detect_brand(response_text, brand_variations, website_domain)
                comps = detect_competitors(response_text, competitors)

                results.append({
                    "query": query_text,
                    "engine": engine_name,
                    "model": engine_info["model"],
                    "response_text": response_text,
                    "brand_mentioned": brand["brand_mentioned"],
                    "brand_cited": brand["brand_cited"],
                    "citation_url": brand["citation_url"],
                    "competitor_mentions": comps,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                status = "MENTIONED" if brand["brand_mentioned"] else "not found"
                if brand["brand_cited"]:
                    status = "CITED"
                print(f"         → {status}")

            except Exception as e:
                print(f"         → ERROR: {e}")

            time.sleep(0.5)

    scores = compute_scores(results, engines)
    return results, scores


def compute_scores(results: list[dict], engines: dict) -> dict:
    per_engine = {}
    for engine_name in engines:
        engine_results = [r for r in results if r["engine"] == engine_name]
        if not engine_results:
            continue
        total = len(engine_results)
        mentions = sum(1 for r in engine_results if r["brand_mentioned"])
        citations = sum(1 for r in engine_results if r["brand_cited"])
        per_engine[engine_name] = {
            "mention_rate": mentions / total,
            "citation_rate": citations / total,
        }

    all_results = [r for r in results if r["engine"] in engines]
    total_all = len(all_results) if all_results else 1
    total_mentions = sum(1 for r in all_results if r["brand_mentioned"])
    total_citations = sum(1 for r in all_results if r["brand_cited"])

    return {
        "per_engine": per_engine,
        "aggregate_mention_rate": total_mentions / total_all,
        "aggregate_citation_rate": total_citations / total_all,
    }
```

- [ ] **Step 2: Commit**

```bash
git add agents/src/tracker.py
git commit -m "feat: tracker orchestrator with scoring"
```

---

## Task 11: CLI Entry Point + End-to-End Run

**Files:**
- Create: `agents/run.py`

- [ ] **Step 1: Implement run.py**

Create `agents/run.py`:

```python
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.tracker import load_client_config, run_tracker
from src.output import write_csv, write_json, format_summary


def main():
    parser = argparse.ArgumentParser(description="GEO Tracker Agent")
    parser.add_argument("config", help="Path to client config JSON file")
    parser.add_argument(
        "--output-dir",
        default="../output",
        help="Directory for output files (default: ../output)",
    )
    args = parser.parse_args()

    config = load_client_config(args.config)
    client_name = config["client_name"]

    print(f"\n  GEO Tracker — {client_name}")
    print(f"  Queries: {len(config['target_queries'])}")
    print(f"  Brand: {config['brand_name']}")
    print()

    results, scores = run_tracker(config)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = client_name.lower().replace(" ", "_")

    csv_path = output_dir / f"{slug}_{timestamp}.csv"
    json_path = output_dir / f"{slug}_{timestamp}.json"

    write_csv(results, csv_path)
    write_json(results, scores, client_name, json_path)

    print(format_summary(scores, client_name))
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run end-to-end against ChildSpot**

```bash
cd /Users/jshum/Desktop/code-folders/vvAgentSystem/agents
source .venv/bin/activate
python run.py ../clients/childspot.json
```

Expected output:
```
  GEO Tracker — ChildSpot
  Queries: 5
  Brand: ChildSpot

  [1/20] chatgpt: best childcare finder in Ontario...
         → MENTIONED
  [2/20] perplexity: best childcare finder in Ontario...
         → not found
  ...

==================================================
  GEO Visibility Report: ChildSpot
==================================================
  chatgpt         mention:    40%   cited:     0%
  perplexity      mention:    20%   cited:    20%
  claude          mention:    60%   cited:    20%
  gemini          mention:    40%   cited:     0%
──────────────────────────────────────────────────
  AGGREGATE       mention:    40%   cited:    10%
==================================================

  CSV:  ../output/childspot_20260616_234500.csv
  JSON: ../output/childspot_20260616_234500.json
```

(Actual percentages will vary based on real LLM responses.)

- [ ] **Step 3: Verify CSV output**

Open the CSV in a spreadsheet app or terminal:

```bash
column -s, -t < ../output/childspot_*.csv | head -5
```

Verify you can read the full `response_text` column and fact-check whether the brand detection was correct.

- [ ] **Step 4: Verify JSON output**

```bash
python -m json.tool ../output/childspot_*.json | head -30
```

Verify the visibility scores and all result entries are present.

- [ ] **Step 5: Commit**

```bash
git add agents/run.py
git commit -m "feat: CLI entry point for tracker agent"
```

---

## Post-Completion: What You Have

After completing all 10 tasks, you have:

1. **A working tracker agent** that queries 4 LLMs with web search enabled
2. **CSV output** with every LLM's full response text for fact-checking visibility scores
3. **JSON output** with structured data + computed visibility scores
4. **Terminal summary** showing per-engine and aggregate mention/citation rates
5. **ChildSpot baseline data** ready for the client call

## What's Next (Phase 2+)

The next implementation plan will cover:
- Supabase schema + persistence (Phase 2-3)
- GSC agent + audit agent (Phase 4)
- Dashboard MVP in Next.js showing GEO metrics (Phase 5)
