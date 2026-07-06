"""Card QA self-review — cheap validation pass before a card surfaces.

Two checks:
1. Grounding (free, programmatic): before_text must actually appear on the page.
2. Haiku judgment (~1 cheap call per card): is after_text specific to this
   page, or generic filler that could apply to any site?

Fail-open on API errors: QA reduces human review load, it must never block
the pipeline. A card that can't be QA'd goes to human review as normal.
"""

import os
import json
import re
import anthropic

HAIKU_MODEL = "claude-haiku-4-5"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def check_grounding(before_text: str, page_text: str) -> dict:
    """Verify before_text is an actual quote from the page (whitespace/case-insensitive)."""
    if not before_text or before_text.strip().lower() == "none":
        return {"passed": True, "reason": "no before_text to check"}
    if _normalize(before_text) in _normalize(page_text):
        return {"passed": True, "reason": "before_text found on page"}
    return {"passed": False, "reason": "before_text not found on page — likely hallucinated"}


def haiku_review(card: dict) -> dict:
    """Ask Haiku whether the proposed change is specific and usable.

    Returns {"verdict": "pass" | "fail" | "error", "reason": str}.
    """
    prompt = f"""You are reviewing a proposed website change before it goes to a human approver.

ACTION TYPE: {card.get('action_type', '')}
PROPOSED REPLACEMENT TEXT:
{card.get('after_text', '')[:1500]}

PROPOSED CODE BLOCK:
{card.get('code_block', '')[:1500]}

Reject the change if ANY of these hold:
- The replacement text is generic filler that could apply to any website
- It contains placeholder tokens like [Brand], [X]%, TODO, lorem, "your company"
- It makes up specific statistics or facts with no plausible source
- It is empty or just restates the problem instead of fixing it

Return ONLY valid JSON: {{"verdict": "pass" or "fail", "reason": "one sentence"}}"""

    try:
        response = _get_client().messages.create(
            model=HAIKU_MODEL,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return {"verdict": "error", "reason": "unparseable Haiku response"}
            data = json.loads(match.group())
        verdict = data.get("verdict", "error")
        if verdict not in ("pass", "fail"):
            verdict = "error"
        return {"verdict": verdict, "reason": data.get("reason", "")}
    except Exception as e:
        print(f"  Card QA: Haiku review failed: {e}")
        return {"verdict": "error", "reason": str(e)}


def qa_card(card: dict, page_text: str) -> dict:
    """Full QA pass. Returns {"passed": bool, "reason": str}."""
    if not card.get("after_text") and not card.get("code_block"):
        return {"passed": False, "reason": "card has no replacement content"}

    grounding = check_grounding(card.get("before_text", ""), page_text)
    if not grounding["passed"]:
        return {"passed": False, "reason": grounding["reason"]}

    review = haiku_review(card)
    if review["verdict"] == "fail":
        return {"passed": False, "reason": review["reason"]}

    # pass or error → fail-open
    return {"passed": True, "reason": review["reason"]}
