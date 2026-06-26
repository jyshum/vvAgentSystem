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
