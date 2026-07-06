import os
import json
import anthropic

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def classify_actions(score_result: dict, page_url: str) -> list[dict]:
    actions = []
    checks = score_result["check_results"]

    if checks["answer_first"]["score"] == 0:
        actions.append({
            "action_type": "restructure_intro",
            "page_url": page_url,
            "issue": checks["answer_first"].get("detail", "Opening paragraph lacks a direct declarative answer"),
        })

    if not checks["faq_schema"].get("has_faq", False):
        actions.append({
            "action_type": "add_faq_schema",
            "page_url": page_url,
            "issue": "No FAQPage schema found — adding FAQ schema improves AI crawler comprehension",
        })

    if checks["source_citations"].get("external_count", 0) == 0:
        actions.append({
            "action_type": "add_citations",
            "page_url": page_url,
            "issue": "No external source citations — pages with 3+ citations are 2.8x more likely to be cited by AI",
        })

    freshness_score = checks["freshness"].get("score", 0)
    if freshness_score <= 3:
        age = checks["freshness"].get("age_days")
        detail = f"Content is {age} days old" if age else "No modification date found"
        actions.append({
            "action_type": "update_freshness",
            "page_url": page_url,
            "issue": f"{detail} — citation rates drop sharply after 3 months",
        })

    schema_status = score_result.get("schema_status", "missing")
    if schema_status == "missing":
        actions.append({
            "action_type": "generate_schema",
            "page_url": page_url,
            "issue": "No JSON-LD schema markup found",
        })
    elif schema_status == "broken":
        errors = score_result.get("schema_errors", [])
        actions.append({
            "action_type": "fix_schema",
            "page_url": page_url,
            "issue": f"Schema has errors: {'; '.join(errors[:3])}",
        })

    return actions


def build_content_brief(
    query: str,
    query_id: str,
    competitive_gap: float,
    top_competitor: str | None,
) -> dict:
    return {
        "query_id": query_id,
        "page_url": None,
        "action_type": "content_brief",
        "track": "manual",
        "priority": 2,
        "competitive_gap": competitive_gap,
        "issue": f"No page exists for query '{query}'" + (f" — {top_competitor} has {competitive_gap:.0%} mention rate advantage" if top_competitor else ""),
        "brief": {
            "target_query": query,
            "competitive_landscape": f"{top_competitor} currently dominates this query" if top_competitor else "No dominant competitor",
            "recommended_title": f"{query.title()} — Complete Guide",
            "recommended_h1": query.title(),
            "key_sections": [
                "Direct answer to the query in the opening paragraph",
                "Comparison of top options (table format)",
                "Detailed analysis with statistics and sources",
                "FAQ section addressing related questions",
            ],
            "facts_to_include": [
                "Industry statistics from authoritative sources (.gov, .edu, .org)",
                "Comparison data between options",
            ],
            "schema_type": "Article",
            "internal_link_targets": [],
            "word_count_target": 2000,
        },
        "status": "pending",
        "cms_action": "none",
    }


def build_reddit_card(query: str, scout_data: dict) -> dict:
    return {
        "page_url": None,
        "action_type": "reddit_engagement",
        "track": "manual",
        "priority": 2,
        "competitive_gap": None,
        "issue": f"{scout_data['threads_found']} Reddit threads found for '{query}' — competitors present in {len(scout_data.get('competitors_mentioned', []))} thread(s)",
        "reddit_data": {
            "threads": scout_data.get("threads", []),
            "competitors_present": scout_data.get("competitors_mentioned", []),
        },
        "status": "pending",
        "cms_action": "none",
    }


CRITICAL_CRAWL_CHECKS = ("robots_txt", "js_rendering", "cdn_blocks")


def build_crawlability_card(crawl_report: dict, domain: str) -> dict:
    failing = [
        name for name in CRITICAL_CRAWL_CHECKS
        if crawl_report.get(name, {}).get("status") == "fail"
    ]
    details = "; ".join(
        crawl_report[name].get("detail") or name for name in failing
    )
    return {
        "page_url": f"https://{domain}",
        "action_type": "fix_crawlability",
        "track": "manual",
        "priority": 0,
        "competitive_gap": None,
        "issue": f"AI crawlers cannot access the site — every other action is blocked until fixed: {details}",
        "status": "pending",
        "cms_action": "none",
    }


def generate_sonnet_specifics(
    page_content: str,
    query: str,
    action_type: str,
    issue: str,
    competitive_gap_info: str,
) -> dict:
    prompt = f"""You are a GEO (Generative Engine Optimization) specialist. Generate a specific, actionable fix.

ACTION TYPE: {action_type}
ISSUE: {issue}
TARGET QUERY: {query}
COMPETITIVE CONTEXT: {competitive_gap_info}

PAGE CONTENT (first 3000 chars):
{page_content[:3000]}

Return ONLY valid JSON with these fields:
{{
    "before_text": "The exact current text that needs to change (quote from page content above, or 'none' if adding new content)",
    "after_text": "The exact replacement text — specific, complete, ready to paste",
    "code_block": "For schema/meta changes: the full JSON-LD or meta tag. Empty string otherwise."
}}

Rules:
- For restructure_intro: rewrite the opening paragraph with a direct declarative answer to the target query in the first sentence
- For add_faq_schema: generate a complete FAQPage JSON-LD block with 3-5 Q&A pairs relevant to the page content
- For add_citations: suggest 3 specific sentences that should include source citations with example authoritative URLs
- For generate_schema: generate Organization + Article/FAQPage JSON-LD appropriate for the page
- For fix_schema: provide the corrected JSON-LD block
- For update_freshness: provide updated meta tag with today's date
- All schema output must include @context and valid @type"""

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return {"before_text": "", "after_text": "", "code_block": ""}

        return {
            "before_text": data.get("before_text", ""),
            "after_text": data.get("after_text", ""),
            "code_block": data.get("code_block", ""),
        }
    except Exception as e:
        print(f"  Sonnet card generation failed: {e}")
        return {"before_text": "", "after_text": "", "code_block": ""}


def generate_sonnet_quality(page_content: str, query: str, check_results: dict) -> dict:
    checks_summary = "\n".join(f"- {k}: {v.get('detail', 'N/A')}" for k, v in check_results.items())

    prompt = f"""You are a GEO specialist. Judge how well this page answers the query for AI citation.

TARGET QUERY: {query}
STRUCTURAL CHECK RESULTS:
{checks_summary}

PAGE CONTENT (first 3000 chars):
{page_content[:3000]}

Return ONLY valid JSON:
{{
    "specificity": 1-5,
    "completeness": 1-5,
    "answer_directness": 1-5,
    "summary": "One sentence assessment"
}}"""

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return {"specificity": 0, "completeness": 0, "answer_directness": 0, "summary": "Sonnet call failed"}

        return {
            "specificity": data.get("specificity", 0),
            "completeness": data.get("completeness", 0),
            "answer_directness": data.get("answer_directness", 0),
            "summary": data.get("summary", ""),
        }
    except Exception as e:
        print(f"  Sonnet quality scoring failed: {e}")
        return {"specificity": 0, "completeness": 0, "answer_directness": 0, "summary": str(e)}


def prioritize_cards(cards: list[dict]) -> list[dict]:
    return sorted(
        cards,
        key=lambda c: (c.get("priority", 3), -(c.get("competitive_gap") or 0)),
    )
