import json
import re
import os
import anthropic

SCORE_THRESHOLD = 60


def _parse_json_response(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fence_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end+1])
        except json.JSONDecodeError:
            pass
    return None

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def should_generate_card(score: int) -> bool:
    return score < SCORE_THRESHOLD


def build_card_prompt(page_url: str, pillar: str, score: int,
                      issues: list[str], page_content: str) -> str:
    return f"""You are a GEO specialist writing a specific, actionable fix for a webpage.

PAGE: {page_url}
PILLAR: {pillar}
CURRENT SCORE: {score}/100
ISSUES FOUND: {chr(10).join(f'- {i}' for i in issues)}

PAGE CONTENT (first 2000 chars):
{page_content[:2000]}

Write ONE action card. Return ONLY valid JSON:
{{
  "issue": "One sentence describing the specific problem on this page",
  "before": "The exact current text that needs to change (quote it directly from the page content above, or write 'none' if adding new content)",
  "after": "The exact replacement text — specific, complete, ready to paste in. For schema pillars, write the full JSON-LD block.",
  "code_block": "If this is a schema or meta tag change, the full code to paste. Otherwise empty string."
}}

Rules:
- 'before' must be actual content from the page, not a description
- 'after' must be complete and ready to use with no placeholders
- For Fact Density: 'after' should be the rewritten paragraph with specific statistics added
- For Content Structure: 'after' should be the rewritten opening paragraph
- For Schema Markup: 'after' should be empty, put the full JSON-LD in 'code_block'
- For Source Citations: 'after' should be the sentence with the citation link added as markdown
- For Authority Signals: 'after' should be a suggested press section or expert quote format
- For Freshness: 'after' should be the updated meta tag with today's date"""


def generate_cards_for_page(page: dict, run_id: str) -> list[dict]:
    cards = []

    for pillar_name, pillar_data in page["pillars"].items():
        score = pillar_data["score"]
        if not should_generate_card(score):
            continue

        issues = pillar_data.get("issues", [])
        if issues and issues[0] == "Haiku scoring unavailable":
            continue
        recommendations = pillar_data.get("recommendations", [])

        if pillar_name == "Authority Signals":
            cards.append({
                "run_id": run_id,
                "page_url": page["url"],
                "pillar": pillar_name,
                "score": score,
                "issue": issues[0] if issues else "No authority signals detected",
                "before_text": "",
                "after_text": "\n".join(recommendations),
                "code_block": "",
                "status": "pending",
                "cms_action": "none",
            })
            continue

        page_content = " ".join(page.get("paragraphs", [])) if "paragraphs" in page else ""

        prompt = build_card_prompt(
            page_url=page["url"],
            pillar=pillar_name,
            score=score,
            issues=issues,
            page_content=page_content,
        )

        try:
            response = _get_client().messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            card_data = _parse_json_response(raw)
            if card_data is None:
                print(f"    Could not parse Haiku response for {pillar_name}: {raw[:200]}")
                continue
        except Exception as e:
            print(f"    Haiku card generation failed for {pillar_name}: {e}")
            continue

        cms_action = "copy_paste"
        if pillar_name == "Schema Markup":
            cms_action = "github_pr"

        cards.append({
            "run_id": run_id,
            "page_url": page["url"],
            "pillar": pillar_name,
            "score": score,
            "issue": card_data.get("issue", ""),
            "before_text": card_data.get("before", ""),
            "after_text": card_data.get("after", ""),
            "code_block": card_data.get("code_block", ""),
            "status": "pending",
            "cms_action": cms_action,
        })

    return cards


def run_recommender(run_id: str, pages: list[dict]) -> list[dict]:
    all_cards = []
    for page in pages:
        print(f"  Generating cards for {page['url']}")
        cards = generate_cards_for_page(page, run_id)
        print(f"    -> {len(cards)} card(s) generated")
        all_cards.extend(cards)
    return all_cards
