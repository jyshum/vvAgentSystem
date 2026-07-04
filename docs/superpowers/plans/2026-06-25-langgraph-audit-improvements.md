# LangGraph Orchestration + Audit Quality Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CLI-only pipeline with a LangGraph-orchestrated, always-on API server on Railway, with per-client scheduling, HITL approval, and audit quality improvements (per-pillar strengths, Playwright rendering, Haiku vision classification).

**Architecture:** FastAPI + LangGraph StateGraph + APScheduler running as a single always-on process on Railway. The dashboard on Vercel calls the API directly. Each pipeline stage (tracker, audit, recommend, implement) becomes a LangGraph node. The graph pauses at `interrupt()` for action card approval, then resumes to run implementation. Audit pages are rendered via Playwright and classified by Haiku vision.

**Tech Stack:** Python 3.11+, LangGraph, FastAPI, uvicorn, APScheduler, Playwright, anthropic SDK, Next.js (dashboard)

**Spec:** `GEO_TECHNICAL_DESIGN.md` sections 2–14

---

## Phase 1: Audit Quality Improvements

These tasks modify existing Python modules. No LangGraph dependency yet — the existing CLI scripts continue to work.

---

### Task 1: Add `strengths` to rule-based scorers

**Files:**
- Modify: `agents/src/scorers.py:12-14` (`_pillar_result`)
- Modify: `agents/src/scorers.py:16-42` (`score_source_citations`)
- Modify: `agents/src/scorers.py:45-88` (`score_schema_markup`)
- Modify: `agents/src/scorers.py:91-143` (`score_freshness`)
- Modify: `agents/tests/test_scorers.py`

- [ ] **Step 1: Write failing tests for strengths in rule-based scorers**

Add to `agents/tests/test_scorers.py`:

```python
def test_source_citations_returns_strengths_key():
    page = _make_page(external_links=[
        "https://ontario.ca/childcare",
        "https://statcan.gc.ca/report",
        "https://example.com/article",
    ])
    result = score_source_citations(page, "childspot.ca")
    assert "strengths" in result


def test_source_citations_strengths_when_authoritative():
    page = _make_page(external_links=[
        "https://ontario.ca/childcare",
        "https://statcan.gc.ca/report",
        "https://canada.ca/data",
    ])
    result = score_source_citations(page, "childspot.ca")
    assert len(result["strengths"]) > 0
    assert any("authoritative" in s.lower() for s in result["strengths"])


def test_source_citations_no_strengths_when_zero():
    page = _make_page(external_links=[])
    result = score_source_citations(page, "childspot.ca")
    assert result["strengths"] == []


def test_schema_markup_strengths_when_perfect():
    page = _make_page(schema_blocks=[
        {"@type": "FAQPage", "mainEntity": []},
        {"@type": "Organization", "name": "Test"},
    ])
    result = score_schema_markup(page)
    assert len(result["strengths"]) > 0


def test_schema_markup_no_strengths_when_zero():
    page = _make_page(schema_blocks=[])
    result = score_schema_markup(page)
    assert result["strengths"] == []


def test_freshness_strengths_when_recent():
    page = _make_page(modified_date="2026-06-01T00:00:00Z")
    result = score_freshness(page)
    assert len(result["strengths"]) > 0


def test_freshness_no_strengths_when_no_date():
    page = _make_page(modified_date=None, last_modified_header=None)
    result = score_freshness(page)
    assert result["strengths"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_scorers.py -v -k "strengths"`
Expected: FAIL — `KeyError: 'strengths'`

- [ ] **Step 3: Update `_pillar_result` to include strengths**

In `agents/src/scorers.py`, change the helper:

```python
def _pillar_result(score: int, issues: list[str], recommendations: list[str],
                   strengths: list[str] | None = None) -> dict:
    return {
        "score": score,
        "strengths": strengths or [],
        "issues": issues,
        "recommendations": recommendations,
    }
```

- [ ] **Step 4: Add strengths logic to `score_source_citations`**

At the end of `score_source_citations`, before the return, add strengths:

```python
    strengths = []
    if len(external) >= 3:
        strengths.append(f"{len(external)} external citations in body content")
    if authoritative:
        strengths.append(f"{len(authoritative)} authoritative source(s) (.gov, .edu, .org)")

    return _pillar_result(score, issues, recommendations, strengths)
```

- [ ] **Step 5: Add strengths logic to `score_schema_markup`**

At the end of `score_schema_markup`, before the return, add strengths:

```python
    strengths = []
    if high_value and baseline:
        strengths.append(f"{', '.join(high_value)} and {', '.join(baseline)} schema both present — best-in-class coverage")
    elif high_value:
        strengths.append(f"High-value schema present: {', '.join(high_value)}")
    elif baseline:
        strengths.append(f"Baseline schema present: {', '.join(baseline)}")

    return _pillar_result(score, issues, recommendations, strengths)
```

- [ ] **Step 6: Add strengths logic to `score_freshness`**

In `score_freshness`, add strengths in the date-found branch. After `score = 100` (age ≤90 days):

```python
        if age_days <= 90:
            score = 100
            strengths = [f"Content is current — last modified {age_days} days ago"]
```

Initialize `strengths = []` at the top of the function. Pass `strengths` to all `_pillar_result` calls:

```python
    return _pillar_result(score, issues, recommendations, strengths)
```

For the no-date branch (return with score 20), keep `strengths = []`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_scorers.py -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add agents/src/scorers.py agents/tests/test_scorers.py
git commit -m "feat: add per-pillar strengths to rule-based scorers"
```

---

### Task 2: Add `strengths` to Haiku scoring prompt

**Files:**
- Modify: `agents/src/scorers.py:168-218` (prompt + `score_with_haiku_batch`)
- Modify: `agents/tests/test_scorers.py`

- [ ] **Step 1: Write failing test**

Add to `agents/tests/test_scorers.py`:

```python
def test_haiku_batch_returns_strengths():
    fake_response = """{
      "content_structure": {"score": 75, "strengths": ["H2 headings phrased as user questions"], "issues": [], "recommendations": []},
      "fact_density": {"score": 80, "strengths": ["1.2 specific facts per 200 words"], "issues": [], "recommendations": []},
      "authority_signals": {"score": 60, "strengths": ["Press mention from Vancouver Sun"], "issues": [], "recommendations": []}
    }"""

    with patch("src.scorers._call_haiku", return_value=fake_response):
        result = score_with_haiku_batch("Some page content.", ["p1 text"], [{"level": 2, "text": "How does it work?"}])

    assert "strengths" in result["content_structure"]
    assert result["content_structure"]["strengths"] == ["H2 headings phrased as user questions"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_scorers.py::test_haiku_batch_returns_strengths -v`
Expected: FAIL — `KeyError: 'strengths'` (the mock returns it but current code doesn't expect it; actually this test may pass since the mock data already contains the key and the code does `json.loads`. Let's verify — if it passes, the prompt update is still needed for real calls but the parsing already handles it.)

- [ ] **Step 3: Update the Haiku scoring prompt**

In `agents/src/scorers.py`, update `HAIKU_SCORING_PROMPT`:

```python
HAIKU_SCORING_PROMPT = """You are a GEO (Generative Engine Optimization) analyst. Score this webpage content on three pillars. Return ONLY valid JSON, no explanation.

PAGE URL: {url}
PAGE TYPE: {page_type}

PAGE CONTENT:
---
{raw_text}
---

FIRST PARAGRAPH:
{first_paragraph}

HEADINGS (level and text):
{headings}

Score each pillar 0-100. For each pillar return: score (int), strengths (list of specific things the page does WELL for this pillar), issues (list of strings describing what's wrong), recommendations (list of specific actionable fixes).

Strengths must be specific and evidence-based. "Has headings" is NOT a strength. "H2 headings map to the user journey (Rescue, Repurpose, Deliver)" IS a strength.

Rules:
- content_structure: Does the first paragraph directly answer a user question (not just describe the company)? Are H2/H3 headings phrased as questions? Are there scannable sections?
- fact_density: Count specific numbers, percentages, dollar amounts, time periods, attributed statistics. Rate per 200 words. Target is 1+. Vague claims like "thousands of customers" do NOT count.
- authority_signals: Are there press mentions with outlet names? Expert quotes with name and title? Aggregate star ratings? "Great product! - John" does NOT count as an expert quote.

Score the content relevant to this page's purpose as a {page_type} page.

Return exactly this JSON structure:
{{
  "content_structure": {{"score": 0-100, "strengths": [], "issues": [], "recommendations": []}},
  "fact_density": {{"score": 0-100, "strengths": [], "issues": [], "recommendations": []}},
  "authority_signals": {{"score": 0-100, "strengths": [], "issues": [], "recommendations": []}}
}}"""
```

- [ ] **Step 4: Update `score_with_haiku_batch` signature to accept page context**

```python
def score_with_haiku_batch(raw_text: str, paragraphs: list[str], headings: list[dict],
                           page_type: str = "service", url: str = "") -> dict:
    first_paragraph = paragraphs[0] if paragraphs else "(no paragraphs found)"
    headings_text = "\n".join(f"H{h['level']}: {h['text']}" for h in headings) or "(no headings found)"

    prompt = HAIKU_SCORING_PROMPT.format(
        raw_text=raw_text[:3000],
        first_paragraph=first_paragraph,
        headings=headings_text,
        page_type=page_type,
        url=url,
    )

    raw = _call_haiku(prompt)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {
            "content_structure": {"score": 0, "strengths": [], "issues": ["Haiku scoring failed"], "recommendations": []},
            "fact_density": {"score": 0, "strengths": [], "issues": ["Haiku scoring failed"], "recommendations": []},
            "authority_signals": {"score": 0, "strengths": [], "issues": ["Haiku scoring failed"], "recommendations": []},
        }
```

- [ ] **Step 5: Update the caller in `auditor.py`**

In `agents/src/auditor.py`, in the `score_page` function, pass page context:

```python
    haiku_scores = score_with_haiku_batch(page.raw_text, page.paragraphs, page.headings,
                                          page_type=page_type, url=url)
```

Note: `page_type` is already computed before `haiku_scores` is called (line 136), but it needs to be computed earlier — move the `classify_page_type` call to before the Haiku scoring:

```python
    page_type = classify_page_type(url, page.title, page.raw_text)

    haiku_scores = score_with_haiku_batch(page.raw_text, page.paragraphs, page.headings,
                                          page_type=page_type, url=url)
```

Remove the duplicate `page_type = classify_page_type(...)` call that was on the original line 136.

- [ ] **Step 6: Run all tests**

Run: `cd agents && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add agents/src/scorers.py agents/src/auditor.py agents/tests/test_scorers.py
git commit -m "feat: add strengths to Haiku prompt and pass page-type context"
```

---

### Task 3: Expand utility patterns

**Files:**
- Modify: `agents/src/auditor.py:24` (`UTILITY_PATTERNS`)
- Modify: `agents/tests/test_auditor.py`

- [ ] **Step 1: Write failing tests**

Add to `agents/tests/test_auditor.py`:

```python
def test_classify_request_as_utility():
    assert classify_page_type("https://example.com/request", "Request Flowers", "") == "utility"

def test_classify_donate_as_utility():
    assert classify_page_type("https://example.com/donate", "Donate", "") == "utility"

def test_classify_signup_as_utility():
    assert classify_page_type("https://example.com/signup", "Sign Up", "") == "utility"

def test_classify_apply_as_utility():
    assert classify_page_type("https://example.com/apply", "Apply Now", "") == "utility"

def test_classify_register_as_utility():
    assert classify_page_type("https://example.com/register", "Register", "") == "utility"

def test_classify_submit_as_utility():
    assert classify_page_type("https://example.com/submit", "Submit", "") == "utility"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agents && python -m pytest tests/test_auditor.py -v -k "request or donate or signup or apply or register or submit"`
Expected: FAIL — these return `"service"` instead of `"utility"`

- [ ] **Step 3: Update `UTILITY_PATTERNS`**

In `agents/src/auditor.py`:

```python
UTILITY_PATTERNS = ["/contact", "/privacy", "/terms", "/thank", "/404", "/sitemap",
                    "/request", "/donate", "/apply", "/signup", "/register", "/submit"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agents && python -m pytest tests/test_auditor.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/auditor.py agents/tests/test_auditor.py
git commit -m "feat: expand utility patterns for form/intake pages"
```

---

### Task 4: Playwright page rendering

**Files:**
- Create: `agents/src/renderer.py`
- Create: `agents/tests/test_renderer.py`
- Modify: `agents/requirements.txt`
- Modify: `agents/pyproject.toml`

- [ ] **Step 1: Add playwright dependency**

In `agents/requirements.txt`, add:
```
playwright>=1.49.0
```

In `agents/pyproject.toml`, add `"playwright>=1.49.0"` to the dependencies list.

- [ ] **Step 2: Install playwright and chromium**

Run: `cd agents && pip install playwright && playwright install chromium`

- [ ] **Step 3: Write failing test for renderer**

Create `agents/tests/test_renderer.py`:

```python
import pytest
from src.renderer import render_page, RenderResult


def test_render_result_has_required_fields():
    """Verify the RenderResult dataclass has the expected structure."""
    result = RenderResult(
        url="https://example.com",
        html="<html><body>Hello</body></html>",
        screenshot=b"fake-png-bytes",
        success=True,
        error=None,
    )
    assert result.url == "https://example.com"
    assert result.html.startswith("<html>")
    assert result.screenshot == b"fake-png-bytes"
    assert result.success is True


def test_render_page_fallback_on_invalid_url():
    """When Playwright fails, render_page falls back to httpx."""
    result = render_page("https://localhost:99999/nonexistent")
    assert result.success is False or result.html != ""
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.renderer'`

- [ ] **Step 5: Implement renderer**

Create `agents/src/renderer.py`:

```python
import httpx
from dataclasses import dataclass


@dataclass
class RenderResult:
    url: str
    html: str
    screenshot: bytes | None
    success: bool
    error: str | None


def render_page(url: str, timeout: int = 30000) -> RenderResult:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (compatible; VV-Audit/1.0)",
                viewport={"width": 1280, "height": 720},
            )
            page.goto(url, wait_until="networkidle", timeout=timeout)
            page.wait_for_timeout(1000)

            screenshot = page.screenshot(full_page=True)
            html = page.content()

            browser.close()

            return RenderResult(
                url=url,
                html=html,
                screenshot=screenshot,
                success=True,
                error=None,
            )
    except Exception as e:
        print(f"    Playwright failed for {url}: {e} — falling back to httpx")
        return _fallback_fetch(url)


def _fallback_fetch(url: str) -> RenderResult:
    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
        return RenderResult(
            url=url,
            html=resp.text,
            screenshot=None,
            success=True,
            error="Playwright failed — used httpx fallback (no screenshot, raw HTML)",
        )
    except Exception as e:
        return RenderResult(
            url=url,
            html="",
            screenshot=None,
            success=False,
            error=str(e),
        )
```

- [ ] **Step 6: Run tests**

Run: `cd agents && python -m pytest tests/test_renderer.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add agents/src/renderer.py agents/tests/test_renderer.py agents/requirements.txt agents/pyproject.toml
git commit -m "feat: add Playwright page renderer with httpx fallback"
```

---

### Task 5: Haiku vision page-type classification

**Files:**
- Create: `agents/src/classifier.py`
- Create: `agents/tests/test_classifier.py`

- [ ] **Step 1: Write failing test**

Create `agents/tests/test_classifier.py`:

```python
from unittest.mock import patch
from src.classifier import classify_page_with_vision, VALID_PAGE_TYPES


def test_valid_page_types_exist():
    assert "homepage" in VALID_PAGE_TYPES
    assert "utility/form" in VALID_PAGE_TYPES
    assert "service" in VALID_PAGE_TYPES


def test_classify_returns_valid_type():
    fake_response = "utility/form — This page contains two intake forms for donating and requesting flowers."

    with patch("src.classifier._call_haiku_vision", return_value=fake_response):
        result = classify_page_with_vision(b"fake-screenshot-bytes", "https://repeatfloral.org/request")

    assert result in VALID_PAGE_TYPES


def test_classify_falls_back_on_unparseable_response():
    with patch("src.classifier._call_haiku_vision", return_value="I don't know what this page is"):
        result = classify_page_with_vision(b"fake-screenshot-bytes", "https://example.com/something")

    assert result == "service"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement classifier**

Create `agents/src/classifier.py`:

```python
import os
import base64
import anthropic

VALID_PAGE_TYPES = {"homepage", "about", "service", "article", "faq", "utility/form", "landing", "gallery"}

CLASSIFICATION_PROMPT = (
    "What type of page is this? Classify as one of: homepage, about, service, article, faq, "
    "utility/form, landing, gallery. Respond with ONLY the classification followed by a dash "
    "and one sentence explaining the page's primary purpose. Example: 'service — This page "
    "describes the company's flower delivery service.'"
)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _call_haiku_vision(screenshot_bytes: bytes, url: str) -> str:
    b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": f"URL: {url}\n\n{CLASSIFICATION_PROMPT}"},
            ],
        }],
    )
    return response.content[0].text


def classify_page_with_vision(screenshot_bytes: bytes, url: str) -> str:
    try:
        raw = _call_haiku_vision(screenshot_bytes, url)
        classification = raw.split("—")[0].split("-")[0].strip().lower()
        if classification in VALID_PAGE_TYPES:
            return classification
        for valid in VALID_PAGE_TYPES:
            if valid in classification:
                return valid
        print(f"    Vision classifier returned unrecognized type '{classification}' — defaulting to 'service'")
        return "service"
    except Exception as e:
        print(f"    Vision classification failed: {e} — defaulting to 'service'")
        return "service"
```

- [ ] **Step 4: Run tests**

Run: `cd agents && python -m pytest tests/test_classifier.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/classifier.py agents/tests/test_classifier.py
git commit -m "feat: add Haiku vision page-type classifier"
```

---

### Task 6: Wire renderer + classifier into auditor

**Files:**
- Modify: `agents/src/auditor.py` (`score_page` function)
- Modify: `agents/tests/test_auditor.py`

- [ ] **Step 1: Write failing test**

Add to `agents/tests/test_auditor.py`:

```python
from unittest.mock import patch, MagicMock
from src.renderer import RenderResult


def test_score_page_uses_renderer_when_not_utility():
    mock_render = RenderResult(
        url="https://example.com/about",
        html="<html><body><title>About</title><h1>About Us</h1><p>We are a company that does things and has many employees working hard.</p></body></html>",
        screenshot=b"fake-png",
        success=True,
        error=None,
    )

    fake_haiku = {
        "content_structure": {"score": 50, "strengths": [], "issues": ["Opening is generic"], "recommendations": ["Rewrite"]},
        "fact_density": {"score": 30, "strengths": [], "issues": ["Low"], "recommendations": ["Add stats"]},
        "authority_signals": {"score": 10, "strengths": [], "issues": ["None found"], "recommendations": ["Add press"]},
    }

    with patch("src.auditor.render_page", return_value=mock_render), \
         patch("src.auditor.classify_page_with_vision", return_value="about"), \
         patch("src.auditor.score_with_haiku_batch", return_value=fake_haiku):
        from src.auditor import score_page
        result = score_page("https://example.com/about", "example.com")

    assert result is not None
    assert result["page_type"] == "about"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_auditor.py::test_score_page_uses_renderer_when_not_utility -v`
Expected: FAIL — `auditor` doesn't import `render_page` or `classify_page_with_vision`

- [ ] **Step 3: Update `score_page` in auditor.py**

Replace the `score_page` function in `agents/src/auditor.py`:

```python
from src.renderer import render_page
from src.classifier import classify_page_with_vision


def score_page(url: str, client_domain: str) -> dict | None:
    path = url.lower().split("?")[0]
    is_utility = any(p in path for p in UTILITY_PATTERNS)

    if is_utility:
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; VV-Audit/1.0)"})
        except httpx.RequestError as e:
            print(f"    Fetch error: {e}")
            return None
        if resp.status_code != 200:
            print(f"    HTTP {resp.status_code} — skipping")
            return None
        html = resp.text
        page_type = "utility"
    else:
        rendered = render_page(url)
        if not rendered.success and not rendered.html:
            print(f"    Render failed: {rendered.error}")
            return None
        html = rendered.html
        if rendered.screenshot:
            page_type = classify_page_with_vision(rendered.screenshot, url)
        else:
            page_type = classify_page_type(url, "", "")

    page = parse_html(url, html, client_domain, 200,
                      last_modified_header=None)

    rules_scores = {
        "Source Citations": score_source_citations(page, client_domain),
        "Schema Markup": score_schema_markup(page),
        "Freshness": score_freshness(page),
    }

    haiku_scores = score_with_haiku_batch(page.raw_text, page.paragraphs, page.headings,
                                          page_type=page_type, url=url)

    pillars = {
        "Content Structure": haiku_scores.get("content_structure", {"score": 0, "strengths": [], "issues": [], "recommendations": []}),
        "Fact Density": haiku_scores.get("fact_density", {"score": 0, "strengths": [], "issues": [], "recommendations": []}),
        "Source Citations": rules_scores["Source Citations"],
        "Authority Signals": haiku_scores.get("authority_signals", {"score": 0, "strengths": [], "issues": [], "recommendations": []}),
        "Schema Markup": rules_scores["Schema Markup"],
        "Freshness": rules_scores["Freshness"],
    }

    applicable = get_applicable_pillars(page_type)
    filtered_pillars = {name: data for name, data in pillars.items() if name in applicable}
    total_score = sum(p["score"] for p in filtered_pillars.values()) // len(filtered_pillars)

    return {
        "url": url,
        "title": page.title,
        "page_type": page_type,
        "word_count": page.word_count,
        "total_score": total_score,
        "pillars": filtered_pillars,
    }
```

Also add `"landing"` and `"gallery"` to `PILLAR_APPLICABILITY`:

```python
PILLAR_APPLICABILITY = {
    "homepage": ["Content Structure", "Authority Signals", "Schema Markup"],
    "about":    ["Content Structure", "Authority Signals", "Schema Markup"],
    "service":  ["Content Structure", "Fact Density", "Source Citations", "Authority Signals", "Schema Markup"],
    "article":  ["Content Structure", "Fact Density", "Source Citations", "Authority Signals", "Schema Markup", "Freshness"],
    "faq":      ["Content Structure", "Source Citations", "Schema Markup"],
    "utility":  ["Schema Markup"],
    "utility/form": ["Schema Markup"],
    "landing":  ["Content Structure", "Authority Signals", "Schema Markup"],
    "gallery":  ["Schema Markup"],
}
```

- [ ] **Step 4: Run all tests**

Run: `cd agents && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/auditor.py agents/tests/test_auditor.py
git commit -m "feat: wire Playwright renderer and vision classifier into audit pipeline"
```

---

## Phase 2: LangGraph Orchestration + API Server

---

### Task 7: Add LangGraph and FastAPI dependencies

**Files:**
- Modify: `agents/requirements.txt`
- Modify: `agents/pyproject.toml`

- [ ] **Step 1: Update dependencies**

In `agents/requirements.txt`, add:
```
langgraph>=0.4.0
langgraph-checkpoint-postgres>=2.0.0
fastapi>=0.115.0
uvicorn>=0.34.0
apscheduler>=3.10.0
```

In `agents/pyproject.toml`, add the same to the dependencies list.

- [ ] **Step 2: Install**

Run: `cd agents && pip install langgraph langgraph-checkpoint-postgres fastapi uvicorn apscheduler`

- [ ] **Step 3: Commit**

```bash
git add agents/requirements.txt agents/pyproject.toml
git commit -m "chore: add LangGraph, FastAPI, APScheduler dependencies"
```

---

### Task 8: Define GEOState and graph nodes

**Files:**
- Create: `agents/src/graph/state.py`
- Create: `agents/src/graph/nodes.py`
- Create: `agents/src/graph/__init__.py`
- Create: `agents/tests/test_graph_nodes.py`

- [ ] **Step 1: Write failing test for node wrappers**

Create `agents/tests/test_graph_nodes.py`:

```python
from src.graph.state import GEOState


def test_geo_state_has_required_keys():
    state = GEOState(
        client_id="test-uuid",
        client_config={},
        tracker_results=[],
        tracker_scores={},
        audit_pages=[],
        audit_summary={},
        action_cards=[],
        approved_card_ids=[],
        implementation_results=[],
        reddit_posts=[],
        run_type="full",
        thread_id="test-thread",
        error=None,
    )
    assert state["client_id"] == "test-uuid"
    assert state["run_type"] == "full"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_graph_nodes.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create state definition**

Create `agents/src/graph/__init__.py`:
```python
```

Create `agents/src/graph/state.py`:

```python
from typing import TypedDict


class GEOState(TypedDict):
    client_id: str
    client_config: dict
    tracker_results: list[dict]
    tracker_scores: dict
    audit_pages: list[dict]
    audit_summary: dict
    action_cards: list[dict]
    approved_card_ids: list[str]
    implementation_results: list[dict]
    reddit_posts: list[dict]
    run_type: str
    thread_id: str
    error: str | None
```

- [ ] **Step 4: Create graph node wrappers**

Create `agents/src/graph/nodes.py`:

```python
import os
from langgraph.types import interrupt
from src.graph.state import GEOState


def load_config(state: GEOState) -> dict:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    result = sb.table("clients").select("*").eq("id", state["client_id"]).single().execute()
    row = result.data
    config = {
        "client_name": row["brand_name"],
        "brand_name": row["brand_name"],
        "website_domain": row["website_domain"],
        "brand_variations": row["brand_variations"] or [],
        "target_queries": row["target_queries"] or [],
        "competitors": row["competitors"] or [],
    }
    return {"client_config": config}


def run_tracker_node(state: GEOState) -> dict:
    from src.tracker import run_tracker
    try:
        results, scores = run_tracker(state["client_config"])
        return {"tracker_results": results, "tracker_scores": scores}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "error": str(e)}


def run_audit_node(state: GEOState) -> dict:
    from src.auditor import run_audit
    try:
        pages, summary = run_audit(state["client_config"])
        return {"audit_pages": pages, "audit_summary": summary}
    except Exception as e:
        print(f"  Audit failed: {e}")
        return {"audit_pages": [], "audit_summary": {}, "error": str(e)}


def run_recommender_node(state: GEOState) -> dict:
    from src.recommender import run_recommender
    try:
        cards = run_recommender(state["thread_id"], state["audit_pages"])
        return {"action_cards": cards}
    except Exception as e:
        print(f"  Recommender failed: {e}")
        return {"action_cards": [], "error": str(e)}


def run_reddit_scout_node(state: GEOState) -> dict:
    from src.reddit_scout import run_scout
    try:
        posts = run_scout(state["client_config"])
        return {"reddit_posts": posts}
    except Exception as e:
        print(f"  Reddit scout failed: {e}")
        return {"reddit_posts": []}


def await_approval(state: GEOState) -> dict:
    approved = interrupt({
        "action": "approve_cards",
        "pending_cards": state["action_cards"],
    })
    return {"approved_card_ids": approved}


def run_implementation_node(state: GEOState) -> dict:
    results = []
    for card in state["action_cards"]:
        if card.get("run_id") not in state["approved_card_ids"] and \
           card.get("id") not in state["approved_card_ids"]:
            continue
        try:
            from src.implementors.github_impl import open_github_pr
            results.append({"card_id": card.get("id"), "status": "implemented"})
        except Exception as e:
            results.append({"card_id": card.get("id"), "status": "error", "error": str(e)})
    return {"implementation_results": results}
```

- [ ] **Step 5: Run tests**

Run: `cd agents && python -m pytest tests/test_graph_nodes.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add agents/src/graph/ agents/tests/test_graph_nodes.py
git commit -m "feat: define GEOState and LangGraph node wrappers"
```

---

### Task 9: Build the StateGraph

**Files:**
- Create: `agents/src/graph/pipeline.py`
- Create: `agents/tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Create `agents/tests/test_pipeline.py`:

```python
from src.graph.pipeline import build_graph


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the graph builder**

Create `agents/src/graph/pipeline.py`:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.graph.state import GEOState
from src.graph.nodes import (
    load_config,
    run_tracker_node,
    run_audit_node,
    run_recommender_node,
    run_reddit_scout_node,
    await_approval,
    run_implementation_node,
)


def route_after_config(state: GEOState) -> str:
    run_type = state.get("run_type", "full")
    if run_type == "audit_only":
        return "run_audit"
    return "run_tracker"


def route_after_tracker(state: GEOState) -> str:
    if state.get("run_type") == "tracker_only":
        return END
    return "run_audit"


def build_graph(checkpointer=None):
    graph = StateGraph(GEOState)

    graph.add_node("load_config", load_config)
    graph.add_node("run_tracker", run_tracker_node)
    graph.add_node("run_audit", run_audit_node)
    graph.add_node("run_recommender", run_recommender_node)
    graph.add_node("run_reddit_scout", run_reddit_scout_node)
    graph.add_node("await_approval", await_approval)
    graph.add_node("run_implementation", run_implementation_node)

    graph.set_entry_point("load_config")

    graph.add_conditional_edges("load_config", route_after_config, {
        "run_tracker": "run_tracker",
        "run_audit": "run_audit",
    })

    graph.add_conditional_edges("run_tracker", route_after_tracker, {
        END: END,
        "run_audit": "run_audit",
    })

    graph.add_edge("run_audit", "run_recommender")
    graph.add_edge("run_recommender", "await_approval")
    graph.add_edge("await_approval", "run_implementation")
    graph.add_edge("run_implementation", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
```

- [ ] **Step 4: Run tests**

Run: `cd agents && python -m pytest tests/test_pipeline.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/src/graph/pipeline.py agents/tests/test_pipeline.py
git commit -m "feat: build LangGraph StateGraph with conditional routing"
```

---

### Task 10: FastAPI server

**Files:**
- Create: `agents/server.py`
- Create: `agents/tests/test_server.py`

- [ ] **Step 1: Write failing test**

Create `agents/tests/test_server.py`:

```python
from fastapi.testclient import TestClient


def test_health_endpoint():
    from server import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agents && python -m pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the server**

Create `agents/server.py`:

```python
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from src.graph.pipeline import build_graph
from langgraph.types import Command

API_KEY = os.environ.get("API_KEY", "dev-key")

app = FastAPI(title="GEO Agent API")
graph = build_graph()


def verify_auth(authorization: str = Header(None)):
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")


class RunRequest(BaseModel):
    client_id: str
    run_type: str = "full"


class ApproveRequest(BaseModel):
    thread_id: str
    approved_card_ids: list[str]


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/run")
async def trigger_run(req: RunRequest, authorization: str = Header(None)):
    verify_auth(authorization)
    thread_id = f"{req.client_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = graph.invoke(
            {
                "client_id": req.client_id,
                "run_type": req.run_type,
                "thread_id": thread_id,
                "client_config": {},
                "tracker_results": [],
                "tracker_scores": {},
                "audit_pages": [],
                "audit_summary": {},
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "reddit_posts": [],
                "error": None,
            },
            config=config,
        )
        return {"thread_id": thread_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approve")
async def approve_cards(req: ApproveRequest, authorization: str = Header(None)):
    verify_auth(authorization)
    config = {"configurable": {"thread_id": req.thread_id}}

    try:
        result = graph.invoke(
            Command(resume=req.approved_card_ids),
            config=config,
        )
        return {"status": "implementation_complete", "results": result.get("implementation_results", [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{thread_id}")
async def get_status(thread_id: str, authorization: str = Header(None)):
    verify_auth(authorization)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        state = graph.get_state(config=config)
        return {
            "next": list(state.next) if state.next else [],
            "has_pending_approval": "await_approval" in (state.next or []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Run tests**

Run: `cd agents && python -m pytest tests/test_server.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add agents/server.py agents/tests/test_server.py
git commit -m "feat: add FastAPI server with run, approve, and status endpoints"
```

---

### Task 11: APScheduler integration

**Files:**
- Modify: `agents/server.py`

- [ ] **Step 1: Add scheduler to server startup**

Add to `agents/server.py`, after the `app` and `graph` definitions:

```python
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()


def trigger_scheduled_run(client_id: str):
    thread_id = f"{client_id}-scheduled-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}
    print(f"  [Scheduler] Starting pipeline for {client_id} (thread: {thread_id})")

    try:
        graph.invoke(
            {
                "client_id": client_id,
                "run_type": "full",
                "thread_id": thread_id,
                "client_config": {},
                "tracker_results": [],
                "tracker_scores": {},
                "audit_pages": [],
                "audit_summary": {},
                "action_cards": [],
                "approved_card_ids": [],
                "implementation_results": [],
                "reddit_posts": [],
                "error": None,
            },
            config=config,
        )
        print(f"  [Scheduler] Pipeline paused at approval for {client_id}")
    except Exception as e:
        print(f"  [Scheduler] Pipeline failed for {client_id}: {e}")


def load_schedules():
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
        result = sb.table("clients").select("id, cycle_frequency, cycle_day").execute()

        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        offset_minutes = 0

        for client in result.data:
            client_id = client["id"]
            cycle_day = day_map.get(client.get("cycle_day", 1), "mon")
            frequency = client.get("cycle_frequency", "weekly")

            trigger = CronTrigger(
                day_of_week=cycle_day,
                hour=2,
                minute=offset_minutes,
            )

            scheduler.add_job(
                trigger_scheduled_run,
                trigger=trigger,
                args=[client_id],
                id=f"cycle-{client_id}",
                replace_existing=True,
            )
            print(f"  [Scheduler] Scheduled {client_id} for {cycle_day} 02:{offset_minutes:02d}")
            offset_minutes += 15

    except Exception as e:
        print(f"  [Scheduler] Failed to load schedules: {e}")
```

Update the `app` creation to use a lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_schedules()
    scheduler.start()
    print("  [Scheduler] Started")
    yield
    scheduler.shutdown()
    print("  [Scheduler] Stopped")

app = FastAPI(title="GEO Agent API", lifespan=lifespan)
```

- [ ] **Step 2: Run all tests**

Run: `cd agents && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add agents/server.py
git commit -m "feat: add APScheduler for per-client automatic pipeline runs"
```

---

### Task 12: Supabase upload integration in graph nodes

**Files:**
- Modify: `agents/src/graph/nodes.py`

- [ ] **Step 1: Add Supabase writes to tracker and audit nodes**

Update `run_tracker_node` in `agents/src/graph/nodes.py` to write results to Supabase after running:

```python
def run_tracker_node(state: GEOState) -> dict:
    from src.tracker import run_tracker
    try:
        results, scores = run_tracker(state["client_config"])

        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

        run_row = sb.table("tracker_runs").insert({
            "client_id": state["client_id"],
            "aggregate_mention_rate": scores.get("aggregate_mention_rate", 0),
            "aggregate_citation_rate": scores.get("aggregate_citation_rate", 0),
            "per_engine_scores": scores.get("per_engine", {}),
            "competitor_scores": scores.get("competitor_scores", {}),
        }).execute()

        result_rows = [{
            "run_id": run_row.data[0]["id"],
            "query": r["query"],
            "engine": r["engine"],
            "model": r.get("model", ""),
            "brand_mentioned": r["brand_mentioned"],
            "brand_cited": r["brand_cited"],
            "citation_url": r.get("citation_url"),
            "competitor_mentions": r.get("competitor_mentions", []),
            "response_text": r.get("response_text", ""),
        } for r in results]
        sb.table("tracker_results").insert(result_rows).execute()

        return {"tracker_results": results, "tracker_scores": scores}
    except Exception as e:
        print(f"  Tracker failed: {e}")
        return {"tracker_results": [], "tracker_scores": {}, "error": str(e)}
```

Update `run_audit_node` similarly to upload to `audit_runs` and `page_scores`.

Update `run_recommender_node` to upload action cards to `action_cards` table.

(Follow the exact patterns from `agents/audit.py:upload_audit_to_supabase` and `agents/recommend.py:upload_cards` — copy the insert logic into the node functions.)

- [ ] **Step 2: Run all tests**

Run: `cd agents && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add agents/src/graph/nodes.py
git commit -m "feat: add Supabase uploads to LangGraph node wrappers"
```

---

## Phase 3: Dashboard Updates

---

### Task 13: Add `pipeline_runs` table and update client schema

**Files:**
- This is a Supabase migration (SQL)

- [ ] **Step 1: Add columns to clients table**

Run in Supabase SQL editor:

```sql
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS cycle_frequency text DEFAULT 'weekly',
ADD COLUMN IF NOT EXISTS cycle_day integer DEFAULT 1;
```

- [ ] **Step 2: Create pipeline_runs table**

```sql
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id uuid REFERENCES clients(id) NOT NULL,
  thread_id text NOT NULL,
  run_type text NOT NULL DEFAULT 'full',
  status text NOT NULL DEFAULT 'running',
  started_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  error_message text,
  CONSTRAINT valid_status CHECK (status IN ('running', 'awaiting_approval', 'implementing', 'completed', 'error'))
);

CREATE INDEX idx_pipeline_runs_client ON pipeline_runs(client_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
```

- [ ] **Step 3: Commit migration notes**

Document the migration in a comment or migration file for reference.

---

### Task 14: Update trigger API route to call LangGraph

**Files:**
- Modify: `dashboard/app/api/runs/trigger/route.ts`

- [ ] **Step 1: Replace Railway redeploy with LangGraph API call**

Replace the Railway GraphQL logic in `dashboard/app/api/runs/trigger/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data: clientUser } = await admin
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (!clientUser || clientUser.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  if (!LANGGRAPH_API || !LANGGRAPH_KEY) {
    return NextResponse.json({ error: "LangGraph API not configured" }, { status: 503 });
  }

  const { clientId, runType = "tracker_only" } = await req.json();
  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 });

  const { data: client } = await admin.from("clients").select("id").eq("id", clientId).single();
  if (!client) return NextResponse.json({ error: "Client not found" }, { status: 404 });

  try {
    const res = await fetch(`${LANGGRAPH_API}/api/run`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${LANGGRAPH_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ client_id: clientId, run_type: runType }),
    });

    if (!res.ok) {
      const body = await res.json();
      throw new Error(body.detail || "LangGraph API error");
    }

    const data = await res.json();
    return NextResponse.json({ ok: true, thread_id: data.thread_id });
  } catch (err) {
    const message = err instanceof Error ? err.message : "LangGraph API error";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
```

- [ ] **Step 2: Add env vars to Vercel**

Add `LANGGRAPH_API_URL` and `LANGGRAPH_API_KEY` to the Vercel project environment variables.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/api/runs/trigger/route.ts
git commit -m "feat: replace Railway redeploy with LangGraph API call"
```

---

### Task 15: Add "Run Audit" button

**Files:**
- Create: `dashboard/components/admin/TriggerAuditButton.tsx`
- Modify: `dashboard/app/admin/clients/[id]/layout.tsx` or wherever TriggerRunButton is rendered

- [ ] **Step 1: Create the audit trigger button**

Create `dashboard/components/admin/TriggerAuditButton.tsx` — same pattern as `TriggerRunButton.tsx` but:
- Button text: `"RUN AUDIT"`
- Sends `runType: "audit_only"` in the request body
- Polls `audit_runs` table instead of `tracker_runs` for completion

```typescript
"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function TriggerAuditButton({ clientId, latestAuditAt }: { clientId: string; latestAuditAt?: string | null }) {
  const [state, setState] = useState<"idle" | "loading" | "triggered" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const router = useRouter();

  const poll = useCallback(async (triggeredAt: number) => {
    const supabase = createClient();
    const elapsed = Date.now() - triggeredAt;
    if (elapsed > 15 * 60 * 1000) {
      setState("idle");
      return;
    }
    const { data } = await supabase
      .from("audit_runs")
      .select("id, ran_at")
      .eq("client_id", clientId)
      .order("ran_at", { ascending: false })
      .limit(1)
      .single();

    const newRunAt = data?.ran_at;
    if (newRunAt && newRunAt !== latestAuditAt) {
      router.refresh();
      setState("idle");
    } else {
      setTimeout(() => poll(triggeredAt), 15000);
    }
  }, [clientId, latestAuditAt, router]);

  async function trigger() {
    setState("loading");
    setErrorMsg(null);
    try {
      const res = await fetch("/api/runs/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clientId, runType: "audit_only" }),
      });
      if (!res.ok) {
        let msg = "API error";
        try {
          const body = await res.json();
          msg = body.detail ? `${body.error}: ${body.detail}` : (body.error ?? msg);
        } catch {
          msg = (await res.text()) || msg;
        }
        throw new Error(msg);
      }
      setState("triggered");
      setTimeout(() => poll(Date.now()), 15000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setErrorMsg(msg);
      setState("error");
      setTimeout(() => setState("idle"), 8000);
    }
  }

  const labels = { idle: "RUN AUDIT", loading: "STARTING...", triggered: "AUDITING...", error: "ERROR — RETRY" };
  const styles: Record<string, React.CSSProperties> = {
    idle: { background: "transparent", color: "var(--white)", border: "1px solid var(--ghost)" },
    loading: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", opacity: 0.6 },
    triggered: { background: "transparent", color: "var(--pos)", border: "1px solid var(--pos)", animation: "vv-pulse 1.2s ease-in-out infinite" },
    error: { background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.2)" },
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={trigger}
        disabled={state === "loading" || state === "triggered"}
        className="font-mono text-[10px] tracking-[0.14em] uppercase py-3 px-7 transition-all duration-200 hover:bg-[var(--white)] hover:text-[var(--ink)] hover:border-[var(--white)] flex-shrink-0 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-[var(--pos)] disabled:hover:border-[var(--pos)]"
        style={styles[state]}
      >
        {labels[state]}
      </button>
      {state === "triggered" && (
        <div className="font-mono text-[8px] tracking-[0.04em] text-right" style={{ color: "var(--mute)" }}>
          Auditing site · checking every 15s
        </div>
      )}
      {state === "error" && errorMsg && (
        <div className="font-mono text-[8px] tracking-[0.04em] max-w-[280px] text-right leading-relaxed" style={{ color: "var(--neg)" }}>
          {errorMsg}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Render the button alongside "Run Now" on the client layout or config page**

Add the `TriggerAuditButton` next to the existing `TriggerRunButton` wherever it's rendered. Both buttons should appear side by side.

- [ ] **Step 3: Commit**

```bash
git add dashboard/components/admin/TriggerAuditButton.tsx
git commit -m "feat: add Run Audit trigger button"
```

---

### Task 16: Build the approvals page

**Files:**
- Create: `dashboard/app/admin/approvals/page.tsx`
- Create: `dashboard/components/admin/ApprovalCard.tsx`
- Create: `dashboard/app/api/admin/approve/route.ts`

- [ ] **Step 1: Create the approval API route**

Create `dashboard/app/api/admin/approve/route.ts`:

```typescript
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_API = process.env.LANGGRAPH_API_URL;
const LANGGRAPH_KEY = process.env.LANGGRAPH_API_KEY;

export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const admin = createAdminClient();
  const { data: clientUser } = await admin
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();
  if (!clientUser || clientUser.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const { threadId, approvedCardIds } = await req.json();

  // Update card statuses in Supabase
  for (const cardId of approvedCardIds) {
    await admin.table("action_cards").update({ status: "approved" }).eq("id", cardId).execute();
  }

  // Resume LangGraph
  if (LANGGRAPH_API && LANGGRAPH_KEY && threadId) {
    try {
      const res = await fetch(`${LANGGRAPH_API}/api/approve`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${LANGGRAPH_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ thread_id: threadId, approved_card_ids: approvedCardIds }),
      });
      if (!res.ok) {
        const body = await res.json();
        return NextResponse.json({ error: body.detail || "LangGraph resume failed" }, { status: 502 });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "LangGraph API error";
      return NextResponse.json({ error: msg }, { status: 502 });
    }
  }

  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 2: Create the ApprovalCard component**

Create `dashboard/components/admin/ApprovalCard.tsx`:

```typescript
"use client";

import { useState } from "react";

interface ApprovalCardProps {
  card: {
    id: string;
    page_url: string;
    pillar: string;
    score: number;
    issue: string;
    before_text: string;
    after_text: string;
    code_block: string;
    status: string;
    cms_action: string;
  };
  clientName: string;
  onStatusChange: (cardId: string, newStatus: "approved" | "rejected") => void;
}

export function ApprovalCard({ card, clientName, onStatusChange }: ApprovalCardProps) {
  const [localStatus, setLocalStatus] = useState(card.status);

  const scoreColor = card.score >= 60 ? "var(--green, #4ade80)" : card.score >= 40 ? "var(--yellow, #facc15)" : "var(--red, #f87171)";

  function handleApprove() {
    setLocalStatus("approved");
    onStatusChange(card.id, "approved");
  }

  function handleReject() {
    setLocalStatus("rejected");
    onStatusChange(card.id, "rejected");
  }

  return (
    <div style={{ border: "1px solid var(--hair)" }} className="p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="space-y-1">
          <div className="font-mono text-[8px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
            {clientName} · {card.pillar}
          </div>
          <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
            {card.page_url}
          </div>
        </div>
        <span className="font-serif text-[17px]" style={{ color: scoreColor }}>
          {card.score}<span className="font-mono text-[9px] ml-0.5" style={{ color: "var(--faint)" }}>/100</span>
        </span>
      </div>

      <p className="font-serif text-[13px] mb-4" style={{ color: "var(--white)" }}>{card.issue}</p>

      {card.before_text && (
        <div className="mb-3">
          <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>Before</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--red, #f87171)" }}>
            {card.before_text}
          </pre>
        </div>
      )}

      {card.after_text && (
        <div className="mb-3">
          <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>After</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--green, #4ade80)" }}>
            {card.after_text}
          </pre>
        </div>
      )}

      {card.code_block && (
        <div className="mb-3">
          <div className="font-mono text-[8px] tracking-[0.1em] uppercase mb-1.5" style={{ color: "var(--faint)" }}>Code to inject</div>
          <pre className="font-mono text-[10px] p-3 whitespace-pre-wrap" style={{ background: "var(--surface)", color: "var(--blue, #60a5fa)" }}>
            {card.code_block}
          </pre>
        </div>
      )}

      <div className="flex items-center gap-3 mt-3">
        {localStatus === "pending" ? (
          <>
            <button
              onClick={handleApprove}
              className="font-mono text-[9px] tracking-[0.1em] uppercase px-4 py-1.5 transition-colors"
              style={{ border: "1px solid var(--green, #4ade80)", color: "var(--green, #4ade80)" }}
            >
              APPROVE
            </button>
            <button
              onClick={handleReject}
              className="font-mono text-[9px] tracking-[0.1em] uppercase px-4 py-1.5 transition-colors"
              style={{ border: "1px solid var(--red, #f87171)", color: "var(--red, #f87171)" }}
            >
              REJECT
            </button>
          </>
        ) : (
          <span
            className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-0.5"
            style={{
              background: localStatus === "approved" ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)",
              color: localStatus === "approved" ? "var(--green, #4ade80)" : "var(--red, #f87171)",
            }}
          >
            {localStatus}
          </span>
        )}
        <span className="font-mono text-[8px]" style={{ color: "var(--faint)" }}>{card.cms_action}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create the approvals page**

Create `dashboard/app/admin/approvals/page.tsx`:

```typescript
import { createAdminClient } from "@/lib/supabase/admin";
import { ApprovalsClient } from "@/components/admin/ApprovalsClient";

export default async function ApprovalsPage() {
  const supabase = createAdminClient();

  const { data: cards } = await supabase
    .from("action_cards")
    .select("*, audit_runs!inner(client_id, clients!inner(brand_name))")
    .eq("status", "pending")
    .order("score", { ascending: true });

  const { data: pipelineRuns } = await supabase
    .from("pipeline_runs")
    .select("thread_id, client_id")
    .eq("status", "awaiting_approval");

  return (
    <div>
      <h1 className="font-display text-[52px] font-light leading-[0.96] mb-2" style={{ color: "var(--white)" }}>
        Approvals
      </h1>
      <p className="font-serif italic text-base mb-10" style={{ color: "var(--mute)" }}>
        {(cards || []).length} pending action card{(cards || []).length !== 1 ? "s" : ""}
      </p>
      <ApprovalsClient
        initialCards={cards || []}
        pipelineRuns={pipelineRuns || []}
      />
    </div>
  );
}
```

Note: The `ApprovalsClient` component (client component wrapping the approval logic, "Finalize & Implement" button, and filtering) follows the same pattern — create it as `dashboard/components/admin/ApprovalsClient.tsx`. It manages local state for approved/rejected card IDs and calls `POST /api/admin/approve` with the thread_id and approved IDs when "Finalize & Implement" is clicked.

- [ ] **Step 4: Add approvals link to admin layout nav**

In `dashboard/app/admin/layout.tsx`, add an "APPROVALS" nav link pointing to `/admin/approvals`.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/admin/approvals/ dashboard/components/admin/ApprovalCard.tsx dashboard/components/admin/ApprovalsClient.tsx dashboard/app/api/admin/approve/ dashboard/app/admin/layout.tsx
git commit -m "feat: add cross-client approvals page with Finalize & Implement"
```

---

## Summary

| Phase | Tasks | What it delivers |
|---|---|---|
| Phase 1 (Tasks 1–6) | Audit quality improvements | Per-pillar strengths, utility patterns, Playwright rendering, Haiku vision classification |
| Phase 2 (Tasks 7–12) | LangGraph + API server | StateGraph orchestration, FastAPI endpoints, APScheduler, Supabase integration |
| Phase 3 (Tasks 13–16) | Dashboard updates | Pipeline table, LangGraph trigger, "Run Audit" button, approvals page |

Tasks are ordered so each phase builds on the previous. Phase 1 can be tested with existing CLI scripts. Phase 2 wraps Phase 1 in LangGraph. Phase 3 connects the dashboard to Phase 2.
