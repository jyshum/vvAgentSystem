import re
from datetime import datetime, timezone


AUTHORITATIVE_TLDS = re.compile(r'\.(gov|edu|org|ac\.[a-z]{2})(/|$)')
RESEARCH_DOMAINS = re.compile(r'(pubmed|ncbi|scholar\.google|statcan|canada\.ca)', re.I)

HIGH_VALUE_SCHEMA = {"FAQPage", "HowTo", "Article", "NewsArticle", "BlogPosting"}
BASELINE_SCHEMA = {"LocalBusiness", "Organization", "Product", "Service", "BreadcrumbList"}


def _pillar_result(score: int, issues: list[str], recommendations: list[str],
                   strengths: list[str] | None = None) -> dict:
    return {"score": score, "strengths": strengths or [], "issues": issues, "recommendations": recommendations}


def score_source_citations(page, client_domain: str) -> dict:
    issues = []
    recommendations = []

    external = [l for l in page.external_links if client_domain not in l]
    authoritative = [l for l in external if AUTHORITATIVE_TLDS.search(l) or RESEARCH_DOMAINS.search(l)]

    if len(external) >= 5:
        base = 70
    elif len(external) >= 3:
        base = 55
    elif len(external) >= 1:
        base = 30
        issues.append(f"Only {len(external)} external citation(s) in body content")
        recommendations.append("Add 3–5 inline links to external sources within the page body")
    else:
        base = 0
        issues.append("No external citations found in body content")
        recommendations.append("Add citations to government, academic, or industry sources directly in the body text — not in nav or footer")

    authority_bonus = min(30, len(authoritative) * 10)
    score = min(100, base + authority_bonus)

    if not authoritative and external:
        recommendations.append("Upgrade at least one citation to a .gov, .edu, or .org source")

    strengths = []
    if len(external) >= 3:
        strengths.append(f"{len(external)} external citations in body content")
    if authoritative:
        strengths.append(f"{len(authoritative)} authoritative source(s) (.gov, .edu, .org)")

    return _pillar_result(score, issues, recommendations, strengths)


def score_schema_markup(page) -> dict:
    issues = []
    recommendations = []

    found_types = set()
    malformed_count = 0

    for block in page.schema_blocks:
        if block.get("_malformed"):
            malformed_count += 1
            continue
        t = block.get("@type")
        if isinstance(t, list):
            found_types.update(t)
        elif t:
            found_types.add(t)

    if malformed_count > 0:
        issues.append(f"{malformed_count} malformed JSON-LD block(s) — crawlers silently ignore these")
        recommendations.append("Validate your schema at schema.org/validator and fix any JSON syntax errors")

    high_value = found_types & HIGH_VALUE_SCHEMA
    baseline = found_types & BASELINE_SCHEMA

    if high_value and baseline:
        score = 100
    elif high_value:
        score = 80
        recommendations.append(f"Add Organization schema alongside {', '.join(high_value)}")
    elif baseline:
        score = 45
        issues.append(f"Only basic schema found: {', '.join(baseline)}")
        recommendations.append("Add FAQPage schema for any FAQ content on this page")
        recommendations.append("Blog posts should have Article schema with dateModified populated")
    elif page.schema_blocks and malformed_count == 0:
        score = 20
        issues.append("Schema blocks found but no recognized @type values")
    else:
        score = 0
        issues.append("No JSON-LD schema markup found")
        recommendations.append("Add FAQPage schema to any page with questions and answers")
        recommendations.append("Add Organization schema to the homepage")

    strengths = []
    if high_value and baseline:
        strengths.append(f"{', '.join(high_value)} and {', '.join(baseline)} schema both present — best-in-class coverage")
    elif high_value:
        strengths.append(f"High-value schema present: {', '.join(high_value)}")
    elif baseline:
        strengths.append(f"Baseline schema present: {', '.join(baseline)}")

    return _pillar_result(score, issues, recommendations, strengths)


def score_freshness(page) -> dict:
    issues = []
    recommendations = []
    strengths = []

    date_str = page.modified_date or page.last_modified_header

    if not date_str:
        match = re.search(
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)'
            r'\s+\d{1,2},?\s+20\d{2}\b',
            page.raw_text
        )
        if match:
            date_str = match.group(0)

    if not date_str:
        issues.append("No publication or modification date found on this page")
        recommendations.append("Add <meta property='article:modified_time' content='YYYY-MM-DDT00:00:00Z'> to the page head")
        recommendations.append("Add a visible 'Last updated [date]' line near the top of the content")
        return _pillar_result(20, issues, recommendations, strengths)

    try:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            from dateutil import parser as dateutil_parser
            dt = dateutil_parser.parse(date_str)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - dt).days

        if age_days <= 90:
            score = 100
            strengths.append(f"Content is current — last modified {age_days} days ago")
        elif age_days <= 180:
            score = 65
            recommendations.append(f"Content is {age_days} days old — add a new section or updated statistic and refresh the modified date")
        elif age_days <= 365:
            score = 35
            issues.append(f"Content is {age_days} days old — over 180 days reduces AI citation likelihood")
            recommendations.append("Rewrite or substantially update this page and set today's date as the modified date")
        else:
            score = 10
            issues.append(f"Content is {age_days} days old — critically stale for AI citation purposes")
            recommendations.append("This page needs a full content refresh. Republish with today's date.")

    except Exception:
        issues.append(f"Could not parse date value: '{date_str}'")
        recommendations.append("Use ISO 8601 format: YYYY-MM-DDT00:00:00Z")
        score = 15

    return _pillar_result(score, issues, recommendations, strengths)


import json
import anthropic

_client = None

def _get_client():
    global _client
    if _client is None:
        import os
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _call_haiku(prompt: str) -> str:
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


HAIKU_SCORING_PROMPT = """You are a GEO (Generative Engine Optimization) analyst. Score this webpage content on three pillars. Return ONLY valid JSON, no explanation.

PAGE CONTENT:
---
{raw_text}
---

FIRST PARAGRAPH:
{first_paragraph}

HEADINGS (level and text):
{headings}

Score each pillar 0-100. For each pillar return: score (int), issues (list of strings describing what's wrong), recommendations (list of specific actionable fixes).

Rules:
- content_structure: Does the first paragraph directly answer a user question (not just describe the company)? Are H2/H3 headings phrased as questions? Are there scannable sections?
- fact_density: Count specific numbers, percentages, dollar amounts, time periods, attributed statistics. Rate per 200 words. Target is 1+. Vague claims like "thousands of customers" do NOT count.
- authority_signals: Are there press mentions with outlet names? Expert quotes with name and title? Aggregate star ratings? "Great product! - John" does NOT count as an expert quote.

Return exactly this JSON structure:
{{
  "content_structure": {{"score": 0-100, "issues": [], "recommendations": []}},
  "fact_density": {{"score": 0-100, "issues": [], "recommendations": []}},
  "authority_signals": {{"score": 0-100, "issues": [], "recommendations": []}}
}}"""


def score_with_haiku_batch(raw_text: str, paragraphs: list[str], headings: list[dict]) -> dict:
    first_paragraph = paragraphs[0] if paragraphs else "(no paragraphs found)"
    headings_text = "\n".join(f"H{h['level']}: {h['text']}" for h in headings) or "(no headings found)"

    prompt = HAIKU_SCORING_PROMPT.format(
        raw_text=raw_text[:3000],
        first_paragraph=first_paragraph,
        headings=headings_text,
    )

    raw = _call_haiku(prompt)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {
            "content_structure": {"score": 0, "issues": ["Haiku scoring failed"], "recommendations": []},
            "fact_density": {"score": 0, "issues": ["Haiku scoring failed"], "recommendations": []},
            "authority_signals": {"score": 0, "issues": ["Haiku scoring failed"], "recommendations": []},
        }
