import os
import re


MENTION_LEVELS = {
    "passing_mention": 1,
    "listed_with_context": 2,
    "recommended": 3,
    "primary_recommendation": 4,
}


def _call_haiku(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip().lower()


def classify_mention_level(response_text: str, brand_name: str) -> dict:
    prompt = (
        f"How is {brand_name} positioned in this AI response? "
        f"Classify as one of: passing_mention, listed_with_context, recommended, primary_recommendation. "
        f"Respond with only the classification.\n\n"
        f"Response:\n{response_text}"
    )
    try:
        label = _call_haiku(prompt)
        label = label.strip().lower().replace(" ", "_")
        if label in MENTION_LEVELS:
            return {"mention_level": MENTION_LEVELS[label], "mention_level_label": label}
    except Exception:
        pass
    return {"mention_level": 1, "mention_level_label": "passing_mention"}


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

    if brand_mentioned:
        matched_variation = next(
            (v for v in brand_variations if v.lower() in text_lower),
            brand_variations[0] if brand_variations else "brand",
        )
        level = classify_mention_level(response_text, matched_variation)
    else:
        level = {"mention_level": 0, "mention_level_label": "not_mentioned"}

    return {
        "brand_mentioned": brand_mentioned,
        "brand_cited": brand_cited,
        "citation_url": citation_url,
        "mention_level": level["mention_level"],
        "mention_level_label": level["mention_level_label"],
    }


def detect_competitors(
    response_text: str,
    competitors: list[str],
) -> list[str]:
    text_lower = response_text.lower()
    return [c for c in competitors if c.lower() in text_lower]
